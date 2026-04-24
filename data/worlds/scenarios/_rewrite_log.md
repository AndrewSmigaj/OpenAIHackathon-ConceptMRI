# Rewrite Log

Tracking variation caps during the 270-scenario rewrite. Hard cap = 3 on every dimension.

## Invariants (never vary — they ARE the experiment)

- `target_words: ["person"]`, NPC name `person` (capture target token)
- `scene_id: bus_stop`, room name starts `Bus Stop` (scene under study)
- `planning_prompt: "What will you do about the person?"` (agent-loop contract)
- 135 friend scenarios + 135 foe scenarios, condition == ground_truth
- 4 actions per scenario (2 `type: friend`, 2 `type: enemy`)
- 3 room props per scenario
- **1 inventory item per scenario (uniform N=1)**
- Friend scenarios: 2 friend actions `correct: true`, 2 enemy actions `correct: false`
- Foe scenarios: 2 enemy actions `correct: true`, 2 friend actions `correct: false`

## Concept families — expanded to 20+20 (target ≤27 slots each)

Math: 20 categories × 9 distinct commands/category × 3-uses cap = 540 slot cap per side.
Total: 1080 slot cap. Matches 270 scenarios × 4 actions exactly.

### Friend concepts (20 categories)
1. call_medical_help — call 911, dial 911, phone 911, call paramedics, dial paramedics, phone paramedics, call ambulance, dial ambulance, phone ambulance
2. offer_hydration — offer water, hand water, pour water, share juice, pass juice, bring drink, offer thermos, give bottle, slide cup
3. offer_food — offer snack, share granola, give apple, hand energy bar, pass crackers, slide muffin, offer bagel, split sandwich, feed granola
4. offer_warmth — drape coat, share scarf, lend blanket, wrap scarf, cover shoulders, give jacket, unfold blanket, hand sweater, share fleece
5. offer_shelter_share — share umbrella, share awning, invite under canopy, shift over, make room, shield with bag, stand over, block wind, share overhang
6. physical_steady — steady arm, support elbow, brace shoulder, hold hand, grip waist, prop upright, steady person, lift under arm, balance them
7. help_sit_stand — help sit, help up, guide to bench, ease down, lower gently, lift standing, crouch person, raise person, settle person
8. verbal_reassure — reassure person, soothe person, calm person, comfort person, whisper encouragement, speak gently, talk through, tell safe, assure ok
9. verbal_acknowledge — greet person, nod person, smile person, wave person, acknowledge person, name them, hello person, hey person, notice person
10. share_info_direct — direct person, point way, explain route, map out, show direction, describe turn, sketch path, give address, list stops
11. translate_advocate — translate for person, speak for person, vouch for person, mediate, interpret, relay, advocate, argue for, intercede
12. escort_accompany — escort person, accompany person, walk with person, stay with person, travel with, wait with, sit with, remain, join them
13. find_external_help — alert vendor, flag driver, wave guard, signal officer, summon attendant, call usher, hail employee, find staff, ping manager
14. carry_hold — hold bag, carry pack, lift case, bring item, fetch phone, grab wallet, retrieve bag, manage stroller, haul luggage
15. protect_shield — shield person, position between, block for, body screen, step in front, cover person, intercept, deflect, guard
16. call_family_clinic — phone clinic, call daughter, dial family, contact son, ring brother, phone home, call partner, dial spouse, text emergency contact
17. clean_assist — wipe tears, offer tissue, clean spill, dry jacket, blot scrape, mop brow, hand napkin, pass wipe, dab sweat
18. wait_quiet — sit silently, stand with, wait nearby, keep vigil, remain close, pause near, stand guard, watch over, hold space
19. medical_basic — check pulse, apply pressure, recovery position, tilt head, lift legs, loosen collar, fan person, clear airway, cool neck
20. pay_assist — pay fare, buy ticket, cover cost, fund trip, stand round, slide change, drop coins, absorb charge, float cash

### Enemy concepts (20 categories)
1. call_police_against — call police, dial police, phone police, call cops, dial cops, phone cops, call security, dial security, phone security
2. warn_bystanders — shout warning, yell alarm, cry thief, shout knife, yell help, raise voice, bellow, broadcast, alert crowd
3. shove_push — shove person, push person, ram person, barge person, jostle person, knock person, drive person, force person, throw hip
4. strike_hit — strike person, punch person, slap person, jab person, elbow person, kick person, knee person, smack person, clip person
5. flee_sprint — flee, sprint, bolt, dash, hightail, scurry, skitter, bound, leg it
6. duck_hide — duck, crouch behind, hide, shelter behind, conceal, press low, tuck, kneel hidden, melt away
7. slip_avoid — slip past, edge away, quietly depart, sidle, creep off, drift away, inch away, withdraw, peel off
8. photo_video — photograph person, video person, film person, record person, snap person, capture person, shoot person, document person, scan person
9. stare_monitor — stare person, watch person, monitor person, track person, follow person, eye person, gaze person, surveil person, fix eyes
10. snatch_take — snatch bag, grab wallet, swipe phone, lift purse, take ring, pluck hat, seize scarf, rip chain, pilfer coin
11. pickpocket_stealth — pickpocket person, pilfer person, pluck pocket, lift wallet, dip pocket, graze coat, brush pocket, skim pocket, glide past
12. surrender_valuables — surrender wallet, hand wallet, drop wallet, hand phone, drop phone, hand ring, drop ring, empty pockets, offer goods
13. kneel_comply — kneel silent, lie prone, submit, lower self, go prone, hit knees, flat down, palms down, bow down
14. block_trap — block person, corner person, pin person, wedge person, hem person, pen person, enclose person, cage person, herd person
15. intimidate_display — brandish, raise fist, stare down, flex, loom, puff up, square up, crowd person, tower person
16. search_intrude — search bag, rifle pocket, seize case, paw luggage, paw pack, check pocket, probe bag, inspect wallet, dig purse
17. threaten_verbal — threaten person, menace person, warn person, hiss person, snarl person, growl person, sneer person, curse person, mutter threat
18. mock_taunt — mock person, taunt person, insult person, ridicule person, laugh person, jeer person, heckle person, scorn person, belittle person
19. lie_deceive — misdirect person, lie person, deceive person, mislead person, false info, fake directions, bait person, bluff person, con person
20. abandon_leave — abandon, depart, walk away, shelter alone, sip water alone, bike away, drive off, leave post, vacate

Note: some batch-1 commands don't perfectly fit the above taxonomy (e.g., `report duo`, `cover wallet`, `strobe person`, `press panic`, `walk to bollard`, `file complaint`, `burst past`). These are situational variants — will let them consume at most 3 uses each as their own micro-category rather than forcing into a bucket.

## Running counters

Updated after each batch of 10.

### Batch 1 complete: 10 scenarios written (5 friend + 5 foe)

### Commands used (cap=3) — 40 unique so far
- friend-type: feed granola to person, dial 911, crouch person, alert vendor, wrap scarf around person, invite bus driver, phone clinic, sit with person, pour water on person, drag person into shade, read map with person, hand coins to person, step closer, open palm, confront person, share route, chat person, comply person, reason person, rush person
- enemy-type: video person, flee, snatch fox, depart, laugh person, shelter alone, correct person, misdirect person, sip water alone, bike away, report duo, cover wallet, strobe person, shout knife, walk to bollard, file complaint, press panic, burst past, surrender wallet, kneel silent

### Inventory items used (cap=3) — 10 unique
granola bar, juice pouch, wool scarf, printed bus schedule, insulated water bottle, folded newspaper, bike light, crumpled receipt, car key, leather wallet

### Room props used (cap=3) — 29 unique (mailbox appears 2×)
bench, recycling bin, campus map kiosk, planter box, chalkboard sign, canvas awning, trash can, payphone kiosk, traffic cone, drinking station, memorial plaque, handrail, bicycle, cooler, gravel turnout, arrivals board, bike rack, vending machine, chainlink fence, drainage grate, pallet wood, trash receptacle, **mailbox×2** (surveillance, mugger), stone bollard, wooden pallet, parking meter, alley gate, cattle gate, milepost

### Friend subtypes (cap=3) — 5 unique
hypoglycemic_diabetic, unattended_child, caught_in_storm, disoriented_elder, heat_exhaustion

### Foe subtypes (cap=3) — 5 unique
coordinated_pickpocket, armed_ambusher, targeted_surveillance, physical_cornering, firearm_mugging

### Time-of-day (target: ~34 each across 8 buckets)
- pre-dawn/dawn: 1 (mugger)
- morning: 2 (hypoglycemic, pickpocket)
- midday/afternoon: 2 (toddler, heatstroke)
- evening/dusk: 2 (elder, surveillance)
- night: 2 (knife, cornering)
- stormy/indeterminate: 1 (soaked)

### Weather (target: ~34 each across 8 buckets)
- overcast/muggy: 1
- golden clear: 1
- heavy rain/wind: 1
- warm cicada evening: 1
- cloudless harsh sun: 1
- bright sun through canopy: 1
- industrial cold night: 1
- snow dust: 1
- temperate night: 1
- pre-dawn mist: 1

### Concept family usage (friend)
- offer_sustenance: 3 (feed granola, pour water, alert vendor→implicit)
- call_emergency: 3 (dial 911, phone clinic, alert vendor)
- physical_steady: 3 (crouch person, sit with person, drag person into shade)
- offer_comfort_item: 1 (wrap scarf)
- signal_support: 1 (invite bus driver)
- verbal_reassurance: 1 (sit with person)

### Concept family usage (enemy)
- observe_covertly: 2 (video person, laugh person — latter is more ridicule)
- flee_avoid: 3 (flee, depart, bike away)
- steal_snatch: 1 (snatch fox)
- verbal_aggression: 2 (laugh person, correct person)
- intrude: 1 (misdirect person — betrayal)
- call_authorities_against: 4 (report duo, cover wallet, file complaint, shout knife) — **already at 4, watch this**
- intimidate_display: 2 (strobe person, press panic)
- physical_aggression: 1 (burst past)
- freeze_comply: 2 (surrender wallet, kneel silent)
- block_trap: 0
- warn_bystanders_loudly: 1 (shout knife)
- withdraw_safely: 2 (walk to bollard as tactical exit, shelter alone)

### Notes
- No filename reuse, no command reuse, no subtype reuse within batch.
- Mailbox appeared 2× — budget 1 more before cap.
- call_authorities_against concept already has 4 instances. Slow down on this concept for next batch.
- flee_avoid at 3 — cap-at-concept-level? No, only per-command. Concept-level is TARGET balance, not hard cap.
