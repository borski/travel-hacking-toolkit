import {createClient} from 'db-vendo-client';
import {profile as dbProfile} from 'db-vendo-client/p/db/index.js';

const client = createClient(dbProfile, 'travel-hacking-toolkit', {enrichStations: false});

const args = process.argv.slice(2);
const command = args[0];

function usage() {
  console.log(`Usage:
  node search_trains.mjs stations <query>
  node search_trains.mjs journeys <from_id_or_name> <to_id_or_name> [--date YYYY-MM-DD] [--time HH:MM] [--results N]
  node search_trains.mjs departures <station_id_or_name> [--date YYYY-MM-DD] [--time HH:MM] [--results N]

Examples:
  node search_trains.mjs stations "Frankfurt Flughafen"
  node search_trains.mjs journeys 8070003 8000376 --date 2026-05-05 --time 10:00
  node search_trains.mjs journeys "Frankfurt Airport" "Germersheim" --date 2026-05-05
  node search_trains.mjs departures 8000244 --results 10
  `);
  process.exit(1);
}

function getArg(flag, defaultVal) {
  const idx = args.indexOf(flag);
  if (idx !== -1 && idx + 1 < args.length) return args[idx + 1];
  return defaultVal;
}

function pad(s, len) {
  s = String(s || '');
  return s.length >= len ? s : s + ' '.repeat(len - s.length);
}

function formatTime(isoStr) {
  if (!isoStr) return '??:??';
  return isoStr.slice(11, 16);
}

function formatDuration(minutes) {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  if (h > 0) return h + 'h ' + m + 'm';
  return m + 'm';
}

async function resolveStation(input) {
  // If it looks like a numeric ID, use it directly
  if (/^\d+$/.test(input)) return input;

  // Otherwise search by name
  const locs = await client.locations(input, {results: 1});
  if (locs.length === 0) {
    console.error('No station found for: ' + input);
    process.exit(1);
  }
  return locs[0].id;
}

async function searchStations(query) {
  const locs = await client.locations(query, {results: 10});
  console.log('Stations matching "' + query + '":\n');
  for (const loc of locs) {
    const typeStr = loc.type || '';
    const products = loc.products
      ? Object.entries(loc.products).filter(([k, v]) => v).map(([k]) => k).join(', ')
      : '';
    console.log('  ' + pad(loc.id, 10) + ' ' + pad(loc.name, 40) + ' ' + pad(typeStr, 10) + ' ' + products);
  }
}

async function searchJourneys(fromInput, toInput) {
  const date = getArg('--date', null);
  const time = getArg('--time', null);
  const results = parseInt(getArg('--results', '5'));

  const fromId = await resolveStation(fromInput);
  const toId = await resolveStation(toInput);

  const opts = {results: results};
  if (date) {
    const timeStr = time || '08:00';
    opts.departure = new Date(date + 'T' + timeStr + ':00+02:00');
  }

  const result = await client.journeys(fromId, toId, opts);

  console.log('Journeys: ' + fromInput + ' → ' + toInput);
  if (date) console.log('Date: ' + date + (time ? ' ' + time : ''));
  console.log('');

  for (let i = 0; i < result.journeys.length; i++) {
    const j = result.journeys[i];
    const firstLeg = j.legs[0];
    const lastLeg = j.legs[j.legs.length - 1];
    const durMin = Math.round((new Date(lastLeg.arrival) - new Date(firstLeg.departure)) / 60000);
    const transfers = j.legs.filter(l => l.line).length - 1;

    console.log('--- Option ' + (i + 1) + ': ' + formatDuration(durMin) + ' (' + transfers + ' transfer' + (transfers !== 1 ? 's' : '') + ') ---');

    for (const l of j.legs) {
      if (!l.line) {
        // Walking transfer
        console.log('  🚶 Walk ' + (l.origin && l.origin.name) + ' → ' + (l.destination && l.destination.name));
        continue;
      }
      const line = l.line.name || l.line.productName || '?';
      const product = l.line.productName || '';
      const dep = formatTime(l.departure);
      const arr = formatTime(l.arrival);
      const from = (l.origin && l.origin.name) || '?';
      const to = (l.destination && l.destination.name) || '?';
      const direction = l.direction ? ' → ' + l.direction : '';
      console.log('  🚆 ' + pad(dep, 6) + '→ ' + pad(arr, 6) + pad(line, 12) + pad(from, 35) + '→ ' + to);
    }
    console.log('');
  }
}

async function searchDepartures(stationInput) {
  const date = getArg('--date', null);
  const time = getArg('--time', null);
  const results = parseInt(getArg('--results', '10'));

  const stationId = await resolveStation(stationInput);

  const opts = {results: results};
  if (date) {
    const timeStr = time || '08:00';
    opts.when = new Date(date + 'T' + timeStr + ':00+02:00');
  }

  const result = await client.departures(stationId, opts);

  console.log('Departures from ' + stationInput + ':\n');
  console.log('  ' + pad('Time', 8) + pad('Line', 14) + pad('Destination', 35) + 'Platform');
  console.log('  ' + '-'.repeat(70));

  for (const d of result.departures) {
    const depTime = formatTime(d.when || d.plannedWhen);
    const line = (d.line && d.line.name) || '?';
    const dest = (d.destination && d.destination.name) || d.direction || '?';
    const platform = d.platform || d.plannedPlatform || '';
    const delay = d.delay ? ' (+' + Math.round(d.delay / 60) + 'm)' : '';
    console.log('  ' + pad(depTime + delay, 14) + pad(line, 14) + pad(dest, 35) + platform);
  }
}

// Main
if (!command) usage();

try {
  switch (command) {
    case 'stations':
      if (!args[1]) usage();
      await searchStations(args[1]);
      break;
    case 'journeys':
      if (!args[1] || !args[2]) usage();
      await searchJourneys(args[1], args[2]);
      break;
    case 'departures':
      if (!args[1]) usage();
      await searchDepartures(args[1]);
      break;
    default:
      console.error('Unknown command: ' + command);
      usage();
  }
} catch (err) {
  console.error('Error: ' + err.message);
  if (err.statusCode) console.error('HTTP ' + err.statusCode);
  process.exit(1);
}
