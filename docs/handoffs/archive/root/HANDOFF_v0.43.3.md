# HANDOFF v0.43.3 - Rider requirements restore 17 items + icons + layer ordering + export

## Key Changes
- **Rider Checklist Restore (17 items):** Fully restored the checklist to the exact 17 items in 4 categories, fully replacing the previous simplified list.
- **Lucide Icons for All Requirements:** Mapped each item to a procedural Lucide icon (Scan, Map, Users, Moon, Home, Table, Armchair, Box, Trash2, Zap, Lightbulb, Droplet, Thermometer, User, ShieldAlert, HeartPulse, Utensils) rather than emojis.
- **Checked Items Persistence:** Each item is interactive, and its state is persisted in  and rendered properly in both screen and print layouts.
- **Layer Reordering and Front Focus:** SVG elements render with fillOpacity 0.7, layer reordering buttons (subir/bajar) work, and selecting any element automatically brings it to the front.
- **Text & SVG Exports:** Implemented Markdown (.md) exports for the checklist, and SVG downloads for the layout.
- **Navigation Unification:** Re-engineered page tabs under 'requirements', 'layout', and 'config' to fix the dead state bug on .
- **Inmutable v0.43.1 Preservation:** Left all supplement flyers and contraportadas completely untouched.
