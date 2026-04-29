---
name: hotel-chains
description: Reference for identifying which loyalty program a hotel belongs to. Maps brand names (Westin, Sheraton, Holiday Inn, etc.) to chain families (Marriott, IHG, Hilton, Hyatt, Accor, etc.) and their loyalty programs. Load when hotel search results contain branded properties, when deciding whether to check award rates, or when a user mentions a hotel name. Triggers on "Marriott", "Hilton", "Hyatt", "IHG", "Sheraton", "Westin", "Holiday Inn", "DoubleTree", "Park Hyatt", "Bonvoy", "Honors", or any branded hotel discussion.
---

# Hotel Chain Recognition

**Reference data:** `data/hotel-chains.json`

Use the `quick_lookup` section in the data file to instantly identify which loyalty program a hotel belongs to when it appears in search results. When you see "Westin" you need to know that's Marriott Bonvoy. When you see "The Standard" you need to know that's Hyatt.

## The Trigger Table

When results contain properties from ANY of these chains, IMMEDIATELY pull AwardWallet balances and check award rates. No judgment call. No asking. Just do it.

| Chain Family | Properties Include | Loyalty Program |
|---|---|---|
| IHG | Holiday Inn, InterContinental, Crowne Plaza, Kimpton, Staybridge, Candlewood | IHG One Rewards |
| Marriott | Marriott, Sheraton, Westin, W, Ritz-Carlton, St. Regis, Courtyard, Aloft | Marriott Bonvoy |
| Hilton | Hilton, DoubleTree, Hampton, Embassy Suites, Waldorf Astoria, Conrad, Curio | Hilton Honors |
| Hyatt | Hyatt, Grand Hyatt, Park Hyatt, Andaz, Thompson, Alila, Hyatt Place | World of Hyatt |
| Accor | Sofitel, Novotel, Pullman, Fairmont, Raffles, Swissôtel, ibis, Mercure | Accor Live Limitless |
| Radisson | Radisson, Radisson Blu, Park Inn, Country Inn | Radisson Rewards |
| Wyndham | Wyndham, Ramada, Days Inn, Super 8, La Quinta, Tryp | Wyndham Rewards |
| Best Western | Best Western, Best Western Plus, Best Western Premier, SureStay | Best Western Rewards |

## Always Compare Points vs Cash for Hotels

- Hyatt points at 1.5cpp floor vs the cash rate. Often a great redemption.
- Hilton at 0.4cpp floor (almost always better to pay cash).
- Marriott at 0.6-0.8cpp depending on category.
- IHG at 0.5-0.7cpp depending on category.

Mention transfer opportunities. "Your Chase UR transfers 1:1 to Hyatt. That 25K/night Category 5 hotel is worth $375 in cash. That's 1.5cpp, right at the floor. Decent but not exceptional."

## Booking Windows for Hotels

Reference `data/sweet-spots.json` `booking_windows` section if a user wants to know how far in advance to book.
