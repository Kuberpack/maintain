# Confirm later — consumables

These are the decisions the store module is running with until someone on the floor says otherwise. None of them block the slips from being used.

1. **Usage standards are placeholders.** Stitching Wire 15/22 Jumbo is seeded at 0.35 kg per 1000 boxes. Maize Starch Powder is 12 kg per ton of board. Modified Starch is 8 kg per ton of board. Real standards (kg of wire per 1000 boxes, kg of starch per ton of board, and any others) still need to come from production. Until then, variance % is only as good as those examples. Standards are optional: a close-out without one still records used / returned / left at the machine.

2. **Missing empty core: warn, do not block.** `CONSUMABLE_CORE_POLICY` defaults to `warn`. A new issue of a roll, tape, or coil still goes through, and the slip (and the issue form) says the previous core has not come back. Set the variable to `block` to refuse the issue. Management and admin can still override a block. Say which behaviour the store wants.

3. **Shift clocks are provisional.** A is 06:00–14:00, B is 14:00–22:00, C is 22:00–06:00, Asia/Kolkata. "Older than 1 shift" means the slip is still open after the *following* shift has also ended (an A-shift slip is flagged from 22:00 the same day). Replace these times when the plant's real shift roster is confirmed.

4. **Carried forward stays on the slip only.** Quantity left at the machine is recorded and is not put back into store stock. It is not automatically offered as the opening issue of the next shift. Say if the next slip should start from that balance.

5. **A physical count changes the book.** Entering a counted quantity stores book qty, counted qty, and the variance, and sets on-hand stock to the count. Say if a count should only be a record and leave the book untouched until someone approves it.

6. **Supervisor signature is the tracked one.** The paper slip's blank supervisor line is a confirmation state: every line must be closed, and any leakage needs a supervisor note, before the slip can be signed. HOD is just a name on the slip, not a login. Issued-by is the person logged in (supervisor, management, or admin). There is no separate storekeeper role — Santosh needs a supervisor (or management) login if his name should appear as issued-by.

7. **Received-by can be any operator**, not only the person assigned to that machine, so a relief operator can sign for the material.

8. **Rupee leakage uses the rate on the slip**, copied when the material was issued. A later rate change on the item master does not rewrite old slips.

9. **Daily sheet returns are negative consumption.** Inward is receipts (and a count that found extra stock). Consumption is issues minus returns, so a MIN on a later day can show a negative consumption figure. Opening + inward − consumption matches the book. Say if returns should be their own column instead.

10. **Slip numbers follow the Indian financial year** (1 April–31 March). 13 Nov 2026 is year 2026-27, slip 01, 02, 03… The sequence does not restart each month.

11. **Leakage in the monthly report is tied to the slip date**, not the day the line was closed. An issue on 30 Nov that is closed on 1 Dec stays in November.
