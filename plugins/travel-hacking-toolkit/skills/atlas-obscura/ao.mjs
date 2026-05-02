#!/usr/bin/env node

// Atlas Obscura hidden gem finder
// Uses: https://github.com/bartholomej/atlas-obscura-api

import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { existsSync } from 'fs';
import { execSync } from 'child_process';

const __dirname = dirname(fileURLToPath(import.meta.url));

// Auto-install dependencies on first run
if (!existsSync(join(__dirname, 'node_modules', 'atlas-obscura-api'))) {
  console.error('Installing atlas-obscura-api (first run only)...');
  execSync('npm install --no-fund --no-audit', { cwd: __dirname, stdio: 'inherit' });
}

const { atlasObscura } = await import('atlas-obscura-api');

const BORING_TAGS = new Set([
  'Plaques', 'Historical Markers', 'Monuments', 'Statues',
  'War Memorials', 'Cemeteries', 'Graves', 'Tombs',
  'Government Buildings', 'Office Buildings'
]);

const INTERESTING_TAGS = new Set([
  'Abandoned', 'Ruins', 'Ghost Towns', 'Underground',
  'Caves', 'Natural Wonders', 'Unusual Collections',
  'Roadside Attractions', 'Hidden Gems', 'Street Art',
  'Bizarre Foods', 'Architectural Oddities', 'Museums',
  'Markets', 'Sacred Sites', 'Hot Springs', 'Waterfalls',
  'Bridges', 'Lighthouses', 'Libraries', 'Bathhouses',
  'Tunnels', 'Mazes', 'Labyrinths', 'Breweries',
  'Distilleries', 'Gardens', 'Parks', 'Islands',
  'Art', 'Sculpture', 'Murals', 'Festivals'
]);

function interestScore(place) {
  let score = 0;
  const tags = (place.tags || []).map(t => t.title || t);

  for (const tag of tags) {
    if (INTERESTING_TAGS.has(tag)) score += 2;
    if (BORING_TAGS.has(tag)) score -= 3;
  }

  // Rich description = more interesting
  if (place.description && place.description.length > 2) score += 2;
  if (place.images && place.images.length > 1) score += 1;

  // "Gone" places are less useful for visiting
  if (place.physical_status === 'gone') score -= 5;
  if (place.hide_from_maps) score -= 5;

  return score;
}

function formatPlace(p, { full = false, images = false } = {}) {
  const out = {
    id: p.id,
    title: p.title,
    subtitle: p.subtitle,
    location: p.location || `${p.city || ''}, ${p.country || ''}`.replace(/^, |, $/g, ''),
    url: p.url?.startsWith('http') ? p.url : `https://www.atlasobscura.com${p.url || ''}`,
    coordinates: p.coordinates
  };

  if (p.distance_from_query) out.distance_km = p.distance_from_query;
  if (p.tags) out.tags = p.tags.map(t => t.title || t);
  if (images && p.thumbnail_url) out.thumbnail = p.thumbnail_url;

  if (full) {
    if (p.description) {
      // Strip HTML tags for clean output
      out.description = (Array.isArray(p.description) ? p.description : [p.description])
        .map(d => d.replace(/<[^>]*>/g, '').replace(/&nbsp;/g, ' ').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').trim())
        .filter(Boolean);
    }
    if (p.directions) {
      out.directions = (Array.isArray(p.directions) ? p.directions : [p.directions])
        .map(d => d.replace(/<[^>]*>/g, '').replace(/&nbsp;/g, ' ').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').trim())
        .filter(Boolean);
    }
    if (images && p.images) out.images = p.images;
    if (images && p.imageCover) out.cover_image = p.imageCover;
    if (p.nearby_places?.length) {
      out.nearby = p.nearby_places.map(n => ({
        id: n.id, title: n.title, subtitle: n.subtitle
      }));
    }
  }

  return out;
}

async function search(lat, lng, { filterBoring = true, images = false } = {}) {
  const response = await atlasObscura.search({ lat: parseFloat(lat), lng: parseFloat(lng) });
  const results = response.results || response;

  if (!filterBoring) return results.map(r => formatPlace(r, { images }));

  // Get full details for top results to score them
  const detailed = [];
  for (const r of results.slice(0, 20)) {
    try {
      const full = await atlasObscura.placeFull(r.id);
      const score = interestScore(full);
      if (score >= 0) {
        detailed.push({ ...formatPlace(full, { full: true, images }), interest_score: score });
      }
    } catch (e) {
      // Skip places that fail to load
      detailed.push(formatPlace(r, { images }));
    }
  }

  return detailed.sort((a, b) => (b.interest_score || 0) - (a.interest_score || 0));
}

async function searchQuick(lat, lng, { images = false } = {}) {
  const response = await atlasObscura.search({ lat: parseFloat(lat), lng: parseFloat(lng) });
  const results = response.results || response;
  return results.map(r => formatPlace(r, { images }));
}

async function placeDetail(id, { images = false } = {}) {
  const place = await atlasObscura.placeFull(parseInt(id));
  const formatted = formatPlace(place, { full: true, images });
  formatted.interest_score = interestScore(place);
  return formatted;
}

async function placeShort(id, { images = false } = {}) {
  const place = await atlasObscura.placeShort(parseInt(id));
  return formatPlace(place, { images });
}

// --- CLI ---
const [,, command, ...args] = process.argv;
const showImages = args.includes('--images');

try {
  let result;

  switch (command) {
    case 'search':
      if (args.filter(a => !a.startsWith('--')).length < 2) {
        console.error('Usage: ao.mjs search <lat> <lng> [--all] [--images]');
        process.exit(1);
      }
      if (args.includes('--all')) {
        result = await searchQuick(args[0], args[1], { images: showImages });
      } else {
        result = await search(args[0], args[1], { images: showImages });
      }
      break;

    case 'quick':
      if (args.filter(a => !a.startsWith('--')).length < 2) {
        console.error('Usage: ao.mjs quick <lat> <lng> [--images]');
        process.exit(1);
      }
      result = await searchQuick(args[0], args[1], { images: showImages });
      break;

    case 'place':
      if (!args[0]) {
        console.error('Usage: ao.mjs place <id> [--images]');
        process.exit(1);
      }
      result = await placeDetail(args[0], { images: showImages });
      break;

    case 'short':
      if (!args[0]) {
        console.error('Usage: ao.mjs short <id> [--images]');
        process.exit(1);
      }
      result = await placeShort(args[0], { images: showImages });
      break;

    default:
      console.error('Commands: search, quick, place, short');
      console.error('  search <lat> <lng>           Nearby places, filtered for interesting stuff');
      console.error('  search <lat> <lng> --all     Nearby places, unfiltered');
      console.error('  quick <lat> <lng>            Fast nearby search (no detail fetch)');
      console.error('  place <id>                   Full place details');
      console.error('  short <id>                   Quick place summary');
      console.error('');
      console.error('Flags:');
      console.error('  --images                     Include image URLs (excluded by default)');
      process.exit(1);
  }

  console.log(JSON.stringify(result, null, 2));
} catch (err) {
  console.error(`Error: ${err.message}`);
  process.exit(1);
}
