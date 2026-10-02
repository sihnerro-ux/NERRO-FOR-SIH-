# Driver disruption workflow

Open http://localhost:8080 and refresh after deployment. Use separate browser profiles for the driver and control room.

1. Sign in as driver@ner.gov.in (DriverDemo@2026). For testing outside NER, register with the explicitly labelled demo GPS option.
2. As the administrator, plan a route and assign the registered vehicle.
3. As driver, acknowledge the assigned route and start the journey.
4. Pause the journey, update GPS and check that it stays paused. Resume to continue.
5. Submit a blocked-road obstruction with a description. The report uses the last accepted vehicle position and remains unverified. Demo GPS reports remain simulated.
6. Review the report in the administrator Incident review panel. Confirmation reassesses affected deliveries. A feasible alternate route creates a new acknowledgement requirement. If no feasible route exists, the journey is held.
7. Acknowledge the latest instruction. A hold acknowledgement does not permit departure; dispatch must resolve the closure and obtain a feasible route.
8. Complete the delivery. Inspect the shared Journey timeline in the driver panel and administrator Deliveries screen.

Instruction acknowledgements carry the version timestamp displayed to the driver. Requests for an older instruction return a conflict and require refreshing the journey. GPS updates cannot release a pause, hold, pending instruction or unstarted driver journey.

## Automatic foreground GPS and handover

For a live registered vehicle, select **Start sharing GPS** in the driver workspace and grant location permission. Fresh fixes with accuracy within 100 metres are uploaded at most once per 10-second interval (plus reconnect attempts). Keep the workspace open and the phone awake. Use HTTPS for phones; plain HTTP LAN addresses cannot provide browser GPS.

Disconnect the network: only the most recent fix is retained in memory. Reconnect: fresh data is submitted automatically; fixes older than 60 seconds are discarded. Check the accepted timestamp, accuracy and stale warnings. Stop sharing or sign out to clear the watch and buffered fix. A delivery assignment/completion changes the tracking session and requires opting in again.

Demo vehicles retain the separate **Advance demo GPS** action and do not start phone tracking. Their coordinates and obstruction reports remain simulated.

At the destination, a driver-managed vehicle now shows `AT_DESTINATION`, retains its assignment and waits for **Mark delivered**. GPS proximity does not prove handover. Confirming delivery releases the vehicle and records the completion in the shared journey timeline.

Current limits: this is foreground browser tracking, not dependable locked-screen/background tracking. The offline GPS buffer is not durable and does not reconstruct historical tracks. Obstruction reporting uses the last recorded vehicle position; update it before reporting. The timeline starts with events recorded after this feature was introduced. No historical events are fabricated. This workflow does not validate the model's predictions on real historical observations.
