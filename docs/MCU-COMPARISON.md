# MCU comparison — observed cmd=48

48 decimal is 0x30, SLEEP. The port sends SLEEP(arg=0x02ff) followed by WAKEUP.

| Path | SLEEP token | Completion wait | Timeout behavior |
|---|---|---|---|
| Linux rt2800pci.c | 2 (TOKEN_RADIO_OFF) | 200 bounded polls | Log, clear status/CID, continue to WAKEUP |
| OpenBSD rt2860.c | 0x30 (command value) | 200 x 100us | Return ETIMEDOUT; init caller ignores result and continues to WAKEUP |
| Current port rt2860.cpp | 0x30 (command value) | 200 x 100us | Sticky io_failed; init short-circuits before WAKEUP and stops |

The token discrepancy is evidence of different implementations, not proof that command-value tokens are invalid. Both write the token and look for it in four CID bytes. Linux completion helper does not require status=1; OpenBSD and port do. Current host tests pass bounded mailbox busy/completion/status error cases but do not simulate real firmware power state.

Confirmed regression in behavior: the port makes the previously ignored SLEEP timeout fatal and skips the following WAKEUP command. Whether the hardware timeout comes from token selection, firmware execution, power state or MMIO ordering remains unconfirmed. Do not remove fault guards or claim the Connect freeze fixed. Native card testing and more mailbox diagnostics are required before selecting a safe power-state recovery change.

References: port/rt2860.cpp:2142,4013; vendor/openbsd/rt2860.c:2023,3872; pinned Linux rt2800pci.c:49,208; rt2800lib.c:515; rt2800.h:3043. Existing kext binaries were not changed by this comparison.
