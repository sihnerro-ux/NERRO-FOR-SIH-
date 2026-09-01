# NER Logistics Control Tower

## Exact User Journeys, Screens, Navigation, and Actions

This document defines how administrators, field officers, and drivers use the MVP. It is the UX source of truth before wireframing or implementation.

---

## 1. Experience principles

The interface must follow these rules:

1. **Operational status comes first.** Users should see blocks, risks, affected deliveries, and stale data before general analytics.
2. **The map is the shared operational picture.** Roads, vehicles, incidents, weather, facilities, and routes must refer to the same map state.
3. **Every decision needs a reason.** A route recommendation or alert must show the factors that produced it.
4. **Confirmed facts and predictions must look different.** A predicted landslide risk is not the same as a verified road block.
5. **Freshness must be visible.** Important data shows its source and last update time.
6. **Critical actions require confirmation.** Confirming a closure, overriding road status, or accepting a reroute cannot happen accidentally.
7. **No route is a valid result.** The interface must not force a misleading alternative.
8. **Field workflows must work one-handed and offline.** Reporting should remain short and usable in poor network conditions.
9. **Colour is not the only signal.** Status always includes text, icon, and colour.
10. **The MVP should tell one connected story.** Screens should support the medicine-delivery disruption scenario rather than becoming unrelated feature pages.

---

## 2. Application structure

The MVP is one responsive Progressive Web Application with role-based experiences.

```text
Sign in
   |
   +-- Control-room administrator -> Desktop control tower
   |
   +-- Field officer -------------> Mobile field workspace
   |
   `-- Driver --------------------> Mobile delivery workspace
```

Users only see navigation and actions allowed by their role.

---

## 3. Global navigation

### 3.1 Administrator desktop navigation

Persistent left sidebar:

```text
NER Logistics
|- Overview
|- Live Map
|- Route Planner
|- Deliveries
|- Fleet
|- Incidents
|- Alerts
|- Analytics
`- Administration
```

Bottom of sidebar:

- Network status
- Data synchronization time
- Language selector
- User profile and sign out

Top application bar:

- Current region/corridor selector
- Global search
- Simulation/live-data mode badge
- Notification centre
- Current time and data freshness
- User menu

### 3.2 Field officer mobile navigation

Persistent bottom navigation:

```text
Home | Nearby | Report | Pending | Profile
```

The centre **Report** action is visually prominent.

### 3.3 Driver mobile navigation

Persistent bottom navigation:

```text
Journey | Route | Alerts | Help
```

The driver sees only the assigned delivery and operational information needed for that journey.

---

## 4. Shared system elements

### 4.1 Status language

Road accessibility:

- Open
- Caution
- High risk
- Partially open
- Blocked
- Unknown

Delivery status:

- Planned
- Assigned
- In transit
- At risk
- Delayed
- Rerouting
- Arrived
- Cancelled

Incident verification:

- Unverified
- Officer verified
- Control-room confirmed
- Resolved
- Expired

Data mode:

- Live
- Simulated
- Cached
- Unavailable

### 4.2 Global search

The administrator can search by:

- Vehicle registration or ID
- Delivery ID
- Road/segment name
- Incident ID
- Hospital or warehouse
- District or settlement

Selecting a result opens its detail panel and focuses the map where appropriate.

### 4.3 Notification centre

Notifications are grouped by:

- Critical
- Warning
- Information

Actions:

- Open related map location
- Open affected delivery
- Acknowledge
- Mark read
- Filter by unread/severity

Acknowledging means the alert was seen. It does not resolve the underlying incident.

### 4.4 Data-source indicator

Every important card or detail panel can display:

```text
Source: Field officer report
Observed: 14:32
Received: 14:36
Status: Control-room confirmed
```

---

## 5. Administrator journey

### Journey A — Begin a control-room shift

**Goal:** Understand regional operating conditions within one minute.

1. Administrator signs in.
2. System opens **Overview**.
3. Header identifies whether the data is live, simulated, cached, or partially unavailable.
4. Administrator sees critical KPIs and unresolved alerts.
5. Map highlights blocked and high-risk segments.
6. Administrator selects a critical alert.
7. The relevant incident, road, vehicles, and deliveries are focused together.

**Successful outcome:** The administrator knows what is disrupted, why it matters, and what requires action.

### Journey B — Plan an emergency delivery

**Goal:** Find a defensible route for medicine from Guwahati to Tawang.

1. Administrator opens **Route Planner**.
2. Selects source facility.
3. Selects destination facility.
4. Chooses cargo type, priority, vehicle class, and departure time.
5. Selects **Calculate routes**.
6. System validates source/destination and current data availability.
7. System returns recommended, fastest, and lowest-risk options where available.
8. Administrator compares distance, ETA, risk, restrictions, and reasons.
9. Selecting a route highlights it on the map and lists its risky segments.
10. Administrator chooses **Use this route**.
11. System asks for vehicle assignment and confirmation.
12. Delivery is created with an auditable route decision.

**Successful outcome:** A vehicle is assigned to a route with visible operational reasoning.

### Journey C — Respond to a reported disruption

**Goal:** Verify impact and protect active deliveries.

1. A field incident arrives through WebSocket.
2. Administrator receives a critical or warning notification.
3. Map focuses the incident and nearest road segment.
4. Incident details show reporter, photo, coordinates, severity, time, and network delay.
5. System displays its suggested segment match.
6. Administrator confirms, adjusts, or rejects the segment match.
7. Administrator verifies the report and confirms the road state.
8. Backend finds active routes using that segment.
9. Affected delivery cards appear.
10. Routing engine recalculates from each vehicle's current position.
11. Administrator reviews the proposed reroute or no-route result.
12. Administrator dispatches the route update/operational instruction.

**Successful outcome:** Every affected delivery has an updated route, holding instruction, or confirmed inaccessible status.

### Journey D — Monitor an active delivery

**Goal:** Verify that an essential shipment is progressing safely.

1. Administrator opens **Deliveries**.
2. Filters by critical priority or at-risk state.
3. Selects a delivery.
4. Delivery detail shows cargo, assigned vehicle, map route, progress, ETA, and event timeline.
5. The administrator inspects upcoming risky segments.
6. If GPS is stale, the interface shows last-known position rather than implying live movement.
7. Administrator can contact/notify the driver or open the route planner from the current position.

**Successful outcome:** The administrator understands present location, schedule, risks, and next required intervention.

### Journey E — Resolve an incident

1. Administrator opens a confirmed incident.
2. Reviews follow-up evidence and newest field observations.
3. Selects **Resolve incident**.
4. Enters resolution note and resulting road status.
5. Confirms the change.
6. Road state and affected route calculations update.
7. The complete history remains in the audit timeline.

---

## 6. Field officer journey

### Journey F — Submit a report online

**Goal:** Report a disruption in under one minute.

1. Officer opens **Report**.
2. Application captures GPS and timestamp.
3. Officer selects incident type.
4. Officer selects severity and observed road accessibility.
5. Officer captures or attaches a photograph.
6. Officer adds an optional short description.
7. Map preview shows the captured location.
8. Officer selects **Submit report**.
9. Application validates required fields and compresses the image.
10. Backend stores the report and proposes the nearest road segment.
11. Officer receives an incident ID and submission status.

### Journey G — Submit a report offline

1. Network banner displays **Offline**.
2. Officer completes the same reporting form.
3. Selects **Save report**.
4. Report is stored in IndexedDB with a unique operation ID.
5. Pending tab shows the report and attachment status.
6. When connectivity returns, synchronization starts.
7. Successful upload returns the official incident ID.
8. Failed items remain pending with a clear retry reason.

The app must not remove the local report until the backend confirms storage.

### Journey H — Update an existing incident

1. Officer opens **Nearby**.
2. Selects the relevant incident.
3. Chooses **Add field update**.
4. Adds current status, photo, and note.
5. Submits online or saves offline.
6. The update becomes a new observation in the incident timeline; it does not overwrite history.

---

## 7. Driver journey

### Journey I — Start an assigned journey

1. Driver signs in and sees the assigned delivery.
2. Reviews cargo, destination, route, estimated duration, and critical warnings.
3. Selects **Start journey**.
4. Confirms GPS permission and vehicle identity.
5. Status becomes **In transit**.
6. GPS updates begin and the control room sees movement.

### Journey J — Receive a disruption warning

1. Driver receives a prominent alert.
2. Alert describes the disruption and distance ahead.
3. Driver opens **Route**.
4. Current path and affected segment are distinguished clearly.
5. If a reroute is approved, the new route and ETA are displayed.
6. Driver selects **Acknowledge route update**.
7. Control room receives the acknowledgement.

The driver does not choose between complex alternatives while driving; the control room sends the approved operational instruction.

### Journey K — No feasible route

1. Driver receives **Stop/Hold instruction**.
2. Screen shows the reason and safe holding location if assigned.
3. Driver acknowledges the instruction.
4. Delivery status becomes **At risk** or **Delayed**.
5. Control room monitors until access is restored or another mode is arranged.

---

## 8. Administrator screen inventory

### 8.1 Sign-in screen

Purpose:

- Authenticate a user and select the correct role experience.

Content:

- Platform identity
- Email/user ID
- Password
- Language selector
- Connectivity indicator
- Demo-account helper in simulated mode only

Actions:

- Sign in
- Show/hide password
- Recover access placeholder

States:

- Loading
- Invalid credentials
- Server unavailable
- Offline: explain that first-time sign-in requires connectivity

### 8.2 Overview

Purpose:

- Provide the command-level operational picture.

Top KPI cards:

- Active vehicles
- Critical deliveries
- Blocked segments
- High-risk segments
- Delayed deliveries
- Unverified incidents

Main content:

- Operational map preview
- Critical alert feed
- Priority delivery list
- Corridor connectivity
- Data-health/freshness panel
- Recent operational timeline

Primary actions:

- Plan a route
- Create a delivery
- Open live map
- Review critical incident

Interactions:

- KPI selection filters the map/list.
- Selecting an alert focuses the related entities.
- Corridor selector updates every component consistently.

### 8.3 Live Map

Purpose:

- Explore the complete spatial operating picture.

Map controls:

- Zoom and recenter
- Base-layer selector
- Layer visibility
- Legend
- Fullscreen
- Current timestamp

Filter drawer:

- Accessibility state
- Risk band
- Incident type and verification
- Vehicle/cargo type
- Delivery priority
- Facility type
- Data freshness

Selectable map objects:

- Road segment
- Incident
- Vehicle
- Delivery route
- Facility
- Weather-risk zone

Selecting an object opens a right-side contextual detail panel without leaving the map.

Actions from the panel:

- Open complete record
- Plan route from/to location
- View affected deliveries
- Verify incident when authorized
- Create alert/manual status override when authorized

### 8.4 Route Planner

Purpose:

- Compare route feasibility, risk, and ETA.

Inputs:

- Source
- Destination
- Cargo type
- Priority
- Vehicle class
- Departure time: now or scheduled
- Risk preference: balanced, safety-first, fastest feasible

Results:

- Recommended route
- Fastest route
- Lowest-risk route
- No-route explanation when applicable

Each route card contains:

- Distance
- ETA
- Overall route risk
- Blocked/restricted segment count
- Highest-risk segment
- Weather exposure
- Added delay compared with fastest
- Recommendation reason
- Data freshness

Actions:

- Highlight route
- Compare route details
- Use route for delivery
- Recalculate
- Export/share summary placeholder

### 8.5 Deliveries

Purpose:

- Manage essential-goods movements.

Table/list columns:

- Delivery ID
- Priority and cargo
- Source/destination
- Vehicle
- Status
- Progress
- ETA
- Delay
- Current route risk
- Last update

Filters:

- Priority
- Cargo type
- Status
- District/corridor
- On schedule/delayed
- At risk

Actions:

- Create delivery
- Open details
- Recalculate route
- Change assignment before departure
- Cancel with reason

### 8.6 Delivery Detail

Sections:

- Delivery summary
- Live map and route
- Vehicle/driver
- ETA and progress
- Upcoming risky segments
- Cargo details
- Alerts
- Event/audit timeline

Actions:

- Open vehicle
- Open incident
- Recalculate route
- Send instruction
- Mark arrived when authorized

### 8.7 Fleet

Purpose:

- Monitor availability and telemetry health.

Columns:

- Vehicle ID/registration
- Vehicle class
- Assigned cargo/delivery
- Driver
- Current status
- Location
- Speed
- GPS freshness
- Route state

Actions:

- Open vehicle
- Locate on map
- Assign available vehicle
- Flag telemetry problem

### 8.8 Vehicle Detail

Content:

- Vehicle and driver identity
- Current/last-known position
- Assigned delivery
- Route and progress
- Current speed
- GPS update history
- Alerts and acknowledgements

GPS states:

- Live
- Delayed
- Stale
- Offline

### 8.9 Incidents

Purpose:

- Review, verify, and resolve field observations.

Columns:

- Incident ID/type
- Location/road segment
- Severity
- Reported accessibility
- Verification state
- Reporter
- Observation time
- Synchronization delay
- Affected deliveries

Actions:

- Review
- Confirm/reject segment match
- Verify
- Confirm road state
- Add note
- Resolve

### 8.10 Incident Detail

Content:

- Type, severity, status
- Map location and matched road
- Original and follow-up photographs
- Reporter and timestamps
- Verification history
- Affected vehicles/deliveries
- System-generated risk impact
- Complete timeline

Any manual change requires a reason.

### 8.11 Alerts

Purpose:

- Manage actionable warnings.

Columns:

- Severity
- Alert type
- Related entity
- Message
- Created time
- Acknowledgement state
- Owner

Actions:

- Open context
- Acknowledge
- Assign owner
- Mark resolved only when the cause is resolved

### 8.12 Analytics

MVP analytics:

- Connectivity by corridor/district
- Road-state distribution
- Incident trend by type
- Delivery on-time rate
- Average disruption delay
- High-risk corridor ranking
- Cargo movement by type

Analytics must show the selected date range and whether data is simulated.

### 8.13 Administration

MVP administration sections:

- Users and roles
- Facilities
- Vehicle registry
- Risk thresholds
- Alert rules
- Data sources and health
- Audit events
- Simulation controls

Simulation controls must be visible only in demo mode and clearly labelled.

---

## 9. Field officer screen inventory

### 9.1 Field Home

Content:

- Online/offline status
- Current GPS quality
- New report button
- Nearby unresolved incidents
- Pending synchronization count
- Latest regional warnings

### 9.2 Nearby

Content:

- Compact map/list toggle
- Nearby incidents
- Nearby risky or blocked roads
- Distance and last update

Actions:

- Open incident
- Add field update
- Start a new report at current location

### 9.3 New Report

Required:

- Incident type
- GPS location
- Observed road accessibility
- Severity

Optional:

- Photo for MVP submission; strongly encouraged
- Description
- Direction/lane information

Actions:

- Refresh GPS
- Capture photo
- Preview location
- Submit online
- Save offline

### 9.4 Pending Sync

Each queued item shows:

- Local report ID
- Incident type
- Created time
- Attachment state
- Retry count
- Last failure reason

Actions:

- Retry
- Edit before upload
- Remove only after explicit confirmation

### 9.5 Field Profile

- Name and district
- Language
- Device/network status
- Last successful synchronization
- Sign out

---

## 10. Driver screen inventory

### 10.1 Journey

Content:

- Delivery and priority
- Cargo
- Destination
- Status
- Progress
- ETA and delay
- Next stop
- Current route warning

Primary actions:

- Start journey
- Acknowledge instruction
- Report vehicle issue
- Confirm arrival

### 10.2 Route

Content:

- Simplified map
- Current location
- Approved route
- Affected/closed road where relevant
- Next risky segment
- Updated route and ETA

The screen avoids complex administrative controls.

### 10.3 Driver Alerts

Displays only alerts relevant to the assigned journey:

- Route changed
- Road disruption ahead
- Hold instruction
- Weather warning
- GPS problem
- Arrival instruction

### 10.4 Help

- Control-room contact
- Emergency action
- Report vehicle breakdown
- GPS/network troubleshooting

---

## 11. Forms and confirmation rules

### Actions that require confirmation

- Confirm road blocked/open
- Reject a field report
- Resolve an incident
- Override automated accessibility
- Dispatch a reroute
- Cancel a delivery
- Remove an unsynchronized report
- Mark a critical delivery arrived manually

Confirmation dialogs must state:

- What will change
- Which vehicles/deliveries are affected
- Whether alerts/rerouting will be triggered
- Required reason when the action is operationally significant

---

## 12. Realtime UI behavior

When a live event arrives, the interface should update without unexpectedly removing the user's current context.

| Event | UI response |
|---|---|
| GPS update | Move vehicle smoothly; update freshness and ETA |
| New field report | Add marker and notification; do not mark road confirmed automatically |
| Confirmed closure | Change segment to red; show affected-delivery alert |
| Risk increase | Change risk styling and show predictive warning |
| Reroute generated | Display proposed route comparison |
| Reroute dispatched | Update driver route and delivery timeline |
| GPS becomes stale | Freeze at last-known location and show stale badge |
| External API failure | Show degraded-data banner and last successful update |

Critical changes may open a notification banner, but should not forcibly navigate the administrator away from an unsaved form.

---

## 13. Required empty, loading, and failure states

Every screen must intentionally handle:

- Initial loading
- No matching data
- No network
- Server unavailable
- Map tiles unavailable
- Weather source unavailable
- Stale GPS
- Stale road information
- Route calculation failed
- No feasible route
- Photo upload failed
- Partial synchronization
- Permission denied

Examples:

- **No route:** `No currently accessible road route was found. Two required segments are confirmed blocked.`
- **Stale GPS:** `Last vehicle position received 24 minutes ago. Position shown is not live.`
- **Weather unavailable:** `Weather feed unavailable. Risk scores are using the last observation from 13:45.`

---

## 14. Desktop and mobile behavior

### Administrator

- Desktop-first layout
- Persistent sidebar
- Large map with contextual right panel
- Tables may collapse into cards on smaller screens
- Critical actions remain accessible without horizontal scrolling

### Field officer and driver

- Mobile-first layout
- Large touch targets
- Minimum typing
- Camera/GPS actions near the thumb zone
- Persistent network/offline indicator
- Forms preserve data if the application closes unexpectedly

---

## 15. Multilingual behavior

The initial interface language will be English, with the application structured for Hindi, Assamese, and additional regional languages.

Rules:

- Language can be changed without losing current work.
- Dynamic road/place names remain as source data provides them.
- Critical alerts use short, plain phrases.
- Status icons and colours remain consistent across languages.
- Offline translation files are included with the PWA shell.

---

## 16. Permission matrix

| Action | Administrator | Field officer | Driver |
|---|:---:|:---:|:---:|
| View regional dashboard | Yes | No | No |
| View all vehicles | Yes | No | No |
| Plan routes | Yes | Nearby/reference only | Assigned route only |
| Create delivery | Yes | No | No |
| Submit incident | Yes | Yes | Limited vehicle issue |
| Verify incident | Yes | No | No |
| Confirm road state | Yes | No | No |
| Dispatch reroute | Yes | No | No |
| Acknowledge reroute | View | No | Yes |
| Resolve incident | Yes | Add evidence only | No |
| Manage users/settings | Yes | No | No |
| Use offline report queue | Optional | Yes | Limited |

---

## 17. Demo-mode controls

To demonstrate the connected workflow reliably, an administrator-only demo panel will provide:

- Reset demo
- Start medicine delivery
- Advance vehicle
- Apply heavy rainfall
- Increase predicted risk
- Submit simulated field report
- Confirm road block
- Generate reroute
- Restore road access

Rules:

- Demo controls are hidden outside simulated mode.
- Every simulated event is labelled `Simulated`.
- Demo actions use the same backend workflows as normal events where possible.
- The UI must not contain unexplained magic buttons on the main dashboard.

---

## 18. Exact two-minute demonstration path

1. Open **Overview** and identify the medicine delivery.
2. Select it to focus the truck and Guwahati-Tawang route.
3. Open the route comparison and show why the current route was recommended.
4. Trigger heavy rainfall near an upcoming mountainous segment.
5. Show predicted risk rising and the segment changing to high risk.
6. Submit/open a field officer landslide report.
7. Confirm the report and change the segment to blocked.
8. Show the system detecting the affected medicine delivery.
9. Show the proposed alternative or explicit no-route outcome.
10. Dispatch the instruction and display the updated ETA.
11. Show the driver's acknowledgement and the event timeline.

This is the primary acceptance journey for the MVP.

---

## 19. Screen implementation priority

### Priority 1 — Required for the connected MVP

1. Sign in/demo entry
2. Administrator Overview
3. Live Map with contextual panel
4. Route Planner
5. Deliveries list and detail
6. Field New Report
7. Incident review/detail
8. Driver Journey/Route
9. Alerts/notifications

### Priority 2 — Operational completeness

10. Fleet and Vehicle Detail
11. Nearby incidents
12. Pending synchronization
13. Analytics

### Priority 3 — Administration and refinement

14. Users and roles
15. Facility/vehicle registries
16. Risk and alert configuration
17. Full audit explorer

The team should complete Priority 1 end-to-end before expanding Priority 2 or 3.

---

## 20. UX acceptance checklist

The UX definition is satisfied when:

- Each role has a clear starting screen.
- Every primary task has a complete success and failure path.
- Map objects open contextual details without losing spatial context.
- Confirmed events and predictions are visually distinct.
- Data source, freshness, and simulation state are visible.
- Blocked and unknown roads cannot appear safely routable.
- No-route results explain why routing failed.
- Offline reports survive reload and synchronize safely.
- Critical administrative actions are confirmed and audited.
- The medicine-delivery disruption story can be completed without navigating through unfinished screens.

