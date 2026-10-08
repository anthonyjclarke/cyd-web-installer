# Copy-in pieces

Files a project copies into its own tree, keeping the same paths. They come
from CYD_AnimatedPixelClock, where they passed the Phase 2 and Phase 5
hardware tests.

---

## `lib/ImprovWiFi/`

This is jnthas *Improv WiFi Library* 0.0.2 (MIT) with one fix, marked
`cyd-web-installer patch`. Versions 0.0.2 to 0.0.4 return the callback's result
after a frame, so the parser keeps the checksum byte as byte 0 of the next
frame. Every second request is then dropped, including ESP Web Tools'
`GET_DEVICE_INFO` after `GET_CURRENT_STATE`, and Connect never offers
**Update**.

Copy it to `lib/ImprovWiFi/`, and remove any `jnthas/Improv WiFi Library`
line from `lib_deps`. With both present, two copies collide.

---

## `src/network/improv_setup.{h,cpp}`

This module keeps Improv-Serial listening on every boot. On a provisioned
device it answers *device info* and *current state*, so ESP Web Tools offers
**Update** with no erase. On a fresh device it also takes WiFi credentials.

It needs these from `include/config.h` and `include/debug.h`:

| Name                    | Kind                          |
|:------------------------|:------------------------------|
| `IMPROV_SETUP_ENABLED`  | `#define` 1 or 0              |
| `PROJECT_NAME`          | string; never change it later |
| `FIRMWARE_VERSION`      | string                        |
| `IMPROV_DEVICE_PREFIX`  | optional `#define`, `"CYD"`   |
| `DBG_INFO` / `DBG_WARN` | leveled debug macros          |

`IMPROV_DEVICE_PREFIX` must be a macro, not a `constexpr`, because it is
pasted into a string literal.

Wire it in three places:

1. Call `improvBegin()` early in `setup()`, right after `Serial.begin()` and
   before WiFi starts.
2. Call `improvTick()` on every `loop()` pass. ESP Web Tools waits only
   1.5 s for an answer on Connect, so a slow loop (anything that blocks for
   more than about 1 s) has to call it more often.
3. While the WiFiManager portal is up, call `improvTick()` from the portal loop
   as well. That means the portal has to run non-blocking:

```cpp
#if IMPROV_SETUP_ENABLED
  wifiManager.setConfigPortalBlocking(false);
#endif
  bool connected = wifiManager.autoConnect(AP_NAME);
#if IMPROV_SETUP_ENABLED
  while (!connected && wifiManager.getConfigPortalActive()) {
    if (wifiManager.process()) { connected = true; break; }
    improvTick();  // restarts once Improv credentials connect
    delay(5);
  }
#endif
```

The connect wait lasts up to 15 s and feeds the task watchdog, so it is safe
to call from `loop()`. If the new network fails, the old credentials are put
back, so a typo in **Change WiFi** can't strand the device. On success the
device restarts onto the new network.

Debug text on the same serial port does no harm, because Improv framing
skips it. Leave it alone.
