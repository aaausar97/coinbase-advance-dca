# Cron Cheatsheet for `DCA_*_USD_CRON`

The bot uses standard 5-field cron expressions interpreted in the timezone set by `TIMEZONE`.

```
*  *  *  *  *
|  |  |  |  |
|  |  |  |  +-- day of week   (0-6, Sun-Sat;  0/7 == Sunday)
|  |  |  +----- month         (1-12)
|  |  +-------- day of month  (1-31)
|  +----------- hour          (0-23)
+-------------- minute        (0-59)
```

## Common DCA recipes


| Goal                                                 | Cron           |
| ---------------------------------------------------- | -------------- |
| Every day at 9:00 AM                                 | `0 9 * * *`    |
| Every Monday at 9:00 AM                              | `0 9 * * 1`    |
| 1st of every month at 9:00 AM                        | `0 9 1 * *`    |
| Every Friday at 5:30 PM                              | `30 17 * * 5`  |
| Twice a week (Mon & Thu, 9 AM)                       | `0 9 * * 1,4`  |
| Every 3 days at noon                                 | `0 12 */3 * *` |
| Every hour (do not actually do this with real money) | `0 * * * *`    |


## Step values

- `*/5 * * * *` → every 5 minutes
- `0 */6 * * *` → every 6 hours, on the hour
- `0 9 */2 * *` → every other day at 9 AM

## Tips

- Test new schedules with `DRY_RUN=true` first.
- The scheduler uses `coalesce=True` and `misfire_grace_time=300`, so if the bot was offline for less than 5 minutes when a job was due, it will run once on startup.
- If the bot is offline for longer, the missed run is skipped (the next scheduled time is honored).

