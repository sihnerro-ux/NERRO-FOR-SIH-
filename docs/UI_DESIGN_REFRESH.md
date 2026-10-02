# NERRO interface refresh

The public homepage and shared operational design system use the supplied NERRO logo, national emblem and tricolour artwork. No political portraits, quotes or named office-holders have been added. The home page explicitly identifies this as an independent SIH prototype, not an official government service or endorsement.

## Design references

- https://www.india.gov.in/ — accessibility controls and service-oriented information hierarchy.
- https://uidai.gov.in/ — identity header, clear primary navigation and task entry points.
- https://www.niti.gov.in/ — spacious public-portal structure.

These informed the structure, not copied content or official branding claims. User-supplied images remain unmodified; the mountain hero is an original code-native illustration, not a geographic map or a live route.

## Updated experience

- Public home with services, workflow, eight-state scope, FAQs and sign-in entry.
- Role-specific sign-in selection with the existing backend authentication unchanged.
- NERRO branding and Home navigation from the operational workspace.
- Shared larger text, spacing, card styles and control sizing across operational modules.
- Text-size controls, keyboard focus indicators, skip links, contrast toggle and reduced-motion support.
- Mobile sidebar close control and backdrop.
- Short hover/press transitions; no continuous decorative animation or forced delays.
- Removed the unconnected global search input from view; the alert shortcut now opens Alerts.
- No changes to dispatch, incident verification, model inference, GPS ownership or permission rules.

## Verification

`frontend/tests/portal-smoke.mjs` uses Playwright with Chrome. It checks home, text resizing, role sign-in, operational navigation, mobile width and runtime page errors without creating deliveries or incidents. Set `PLAYWRIGHT_MODULE` to the installed Playwright module URL if it is not resolvable as a package; `NERRO_TEST_URL` defaults to localhost:8080.

Screenshots default to the git-ignored `.local-tunnel/ui` directory. The smoke check is not a complete accessibility certification or an end-to-end test of every business action.

The service-worker shell cache version has been updated to include the supplied identity assets. Refresh an existing browser tab after deployment. Rebuilding the frontend container may require restarting the temporary tunnel gateway to refresh its upstream address; the tunnel itself need not be restarted.
