# ISSUE-008: Chart UI Controls Overlap

**Status**: Done ✅
**Priority**: P1 (High)
**Type**: Bug
**Created**: 2026-01-17
**Completed**: 2026-01-20
**Assignee**: Frontend Engineer

## Problem Description
The timeframe selector and zoom controls were overlapping with the chart's price axis or other UI elements, making them difficult to use.

## Acceptance Criteria
- [x] Group timeframe selector and zoom controls together.
- [x] Position them on the right-top of the chart, avoiding overlap with the price axis.
- [x] Ensure they are visible and functional across different screen sizes.

## Technical Details
- **Implementation**: Grouped in `App.tsx` at `absolute top-3 right-16`.
- **Controls**: Includes `TimeframeSelector`, Zoom In/Out, and Reset Zoom.
- **Styling**: Uses `glass` background and `z-10` to stay above the chart.
