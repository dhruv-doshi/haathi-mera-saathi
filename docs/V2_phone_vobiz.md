# V2 — Phone Mentor via Vobiz (reach anywhere)

Depends on: **Foundation (0.x).** Goal: the same Saathi, dial-able on a real phone number. Uses **Vobiz credits** (the only credit V2 needs).

> Build only after V1 is solid. SIP is the classic time-sink — never let it block V1. The brain does not change; you are only attaching a phone channel.

Path (confirmed): **Vobiz DID + SIP trunk → LiveKit inbound SIP trunk + dispatch rule → room → Foundation agent joins as the caller's conversation partner.**

---

## Phase 2.1 — Vobiz number + outbound trunk to LiveKit

▶ **Quote to Claude Code:**
> Walk me through configuring Vobiz: confirm an active Indian DID, and set up a SIP trunk that routes inbound calls on that number to LiveKit's SIP ingress URI. List exactly which Vobiz values I must copy (SIP URI/host, credentials, number) and where each goes. Do not write app code in this phase — this is provider configuration.

✅ **Accept when:**
- A Vobiz number is active and its SIP trunk targets LiveKit's SIP endpoint.
- You have the credentials/URI noted for Phase 2.2.

---

## Phase 2.2 — LiveKit inbound SIP trunk + dispatch rule

▶ **Quote to Claude Code:**
> Configure a LiveKit inbound SIP trunk that accepts calls from Vobiz, and a dispatch rule that routes each inbound call into a room and dispatches the Foundation agent into it. Keep config in files I can review. The agent code from Foundation must run unchanged.

✅ **Accept when:**
- An inbound call lands in a LiveKit room with the agent present.
- No changes were made to the Mentor Brain itself.

---

## Phase 2.3 — Telephony parity tuning

▶ **Quote to Claude Code:**
> Adjust only for the phone channel: handle narrowband (8 kHz) telephony audio, confirm the chosen STT/TTS work over the phone path, greet on call-connect, and tune VAD/endpointing so interruption feels right on a call. No new features.

✅ **Accept when:**
- Voice quality and turn-taking feel natural on a real call.
- Interruption works over the phone.

---

## Phase 2.4 — Live call test

▶ **Quote to Claude Code:**
> Help me run and debug a live call: I dial the Vobiz number, Saathi answers with my context, I run the V1 demo flow (doubt → personal → breathing reset → next step) over the phone, and the call ends cleanly with a saved memory summary.

✅ **Accept when (V2 acceptance gate):**
- Dialing connects within a few rings.
- Mentor behaviour, banter, and energize match V1.
- Clean hang-up, no dangling sessions.

---

### Out of scope for V2
Outbound/bulk calling, IVR menus, multi-number routing, recording/analytics.
