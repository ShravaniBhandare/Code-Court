# Code Quality Signal

- Function quality combines complexity (60%), size (25%), and parameter count (15%).
- Complexity scores are 0.30 for the simplest functions, peak at 1.0 for values 3-15, and decline to 0.2 above 39.
- Function size scores 1.0 through 40 NLOC, then decline linearly to 0.3 at 150 NLOC.
- Parameter scores remain 1.0 through four parameters, decline to 0.5 at eight, and are 0.4 above eight.
- A function is touched only when at least two non-blank added lines fall inside its Lizard range.
- Quality changes later size calculations only through the bounded 0.7-1.2 modifier.
- Authors with fewer than five analyzed functions receive a neutral modifier of 1.0 and are marked low-confidence.
