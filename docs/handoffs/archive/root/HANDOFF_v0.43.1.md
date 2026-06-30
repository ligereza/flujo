# HANDOFF v0.43.1 - Automatic Back Covers & Vertical Flyers

## Key Changes
- **Flyers & Labels Vertical Alignment:** Swapped all supplement flyers to vertical 10x14 cm (2000x2800 px) in , index and config JSONs.
- **Microsecond Performance Optimization:** Switched character width calculation to highly accurate linear estimation, reducing generation time to 1.6 seconds.
- **Dynamic Supplement Lookup:** Merged dictionary and spec JSON lookup, seamlessly supporting 11 products.
- **Automatic Contraportadas:** Hub now automatically triggers SVG contraportada generation on job creation when area=suplementos, with optional regex brief override.
- **Manuals and style guide:** Created  and added Section H to .
- **Hobby Cleanup:** Mapped and archived 15+ redundant / obsolete files to  to keep the repo clean and tidy.
