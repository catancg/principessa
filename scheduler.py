from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from app.db.session import SessionLocal
from app.jobs.weekly_scheduler import queue_weekly_promo
from datetime import datetime, timezone

def run_weekly():
    print("RUN weekly", flush=True)
    db = SessionLocal()
    try:
        info = queue_weekly_promo(db)
        print("Weekly queue:", info)
    finally:
        db.close()

if __name__ == "__main__":
    sched = BlockingScheduler(timezone="UTC")

    trigger = CronTrigger(day_of_week="mon", hour=17, minute=50, timezone="UTC")
    job = sched.add_job(run_weekly, trigger, id="weekly", replace_existing=True)

    now = datetime.now(timezone.utc)

    # Compute next fire time without relying on job.next_run_time
    next_run = job.trigger.get_next_fire_time(previous_fire_time=None, now=now)

    print("Scheduler started", flush=True)
    print(f"Now (UTC):      {now}", flush=True)
    print(f"Next run (UTC): {next_run}", flush=True)
    if next_run:
        print(f"Time left:      {next_run - now}", flush=True)

    # This will "freeze" the terminal by design (BlockingScheduler blocks)
    try:
        sched.start()
    except (KeyboardInterrupt, SystemExit):
        print("Scheduler shutting down...", flush=True)
        sched.shutdown()