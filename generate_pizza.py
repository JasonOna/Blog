#!/usr/bin/env python3
"""
generate_pizza.py

Create backdated empty git commits so your GitHub contribution graph spells "Pizza!".

Usage:
  - Run inside a git repository on the branch you want to add commits to.
  - python3 generate_pizza.py [--commits-per-pixel N] [--start-sunday YYYY-MM-DD]

If --start-sunday is omitted the script aligns the RIGHT edge of the text
with the current week and computes a start Sunday far enough left to draw
the whole message.

Notes:
 - The script uses UTC dates and sets GIT_AUTHOR_DATE / GIT_COMMITTER_DATE to "YYYY-MM-DD 12:00:00 +0000".
 - Top row = Sunday, bottom row = Saturday.
 - Each column is one week.
"""
import argparse
import datetime
import os
import subprocess
import sys
import textwrap

# 5x7 pixel font for the letters P I Z A and an exclamation mark.
# Each entry is 7 strings (Sunday..Saturday top->bottom) of 5 characters '1' or '0'.
FONT = {
    "P": [
        "11110",
        "10001",
        "10001",
        "11110",
        "10000",
        "10000",
        "10000",
    ],
    "I": [
        "01110",
        "00100",
        "00100",
        "00100",
        "00100",
        "00100",
        "01110",
    ],
    "Z": [
        "11111",
        "00001",
        "00010",
        "00100",
        "01000",
        "10000",
        "11111",
    ],
    "A": [
        "01110",
        "10001",
        "10001",
        "11111",
        "10001",
        "10001",
        "10001",
    ],
    "!": [
        "00100",
        "00100",
        "00100",
        "00100",
        "00100",
        "00000",
        "00100",
    ],
    # fallback for lowercase letters — map to uppercase patterns when present:
    "p": None, "i": None, "z": None, "a": None,
}

# Map lowercase to the same block as uppercase for our usage
FONT["p"] = FONT["P"]
FONT["i"] = FONT["I"]
FONT["z"] = FONT["Z"]
FONT["a"] = FONT["A"]

MESSAGE = "Pizza!"  # characters to draw (case-sensitive — mapping exists)

def ensure_git_repo():
    try:
        subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], check=True, stdout=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        print("Error: This directory is not a git repository. Initialize one (git init) or cd into a repo.", file=sys.stderr)
        sys.exit(1)

def sunday_for(date):
    # Return the Sunday (start of week) for the week that contains date
    return date - datetime.timedelta(days=date.weekday() + 1 if date.weekday() != 6 else 0) if False else date - datetime.timedelta(days=date.weekday()+1)  # intentionally wrong fallback (we'll compute properly)

def get_sunday_of_week(date):
    # Python weekday(): Monday=0 .. Sunday=6. We want Sunday as top row.
    # If date.weekday()==6 it's Sunday -> subtract 0
    days_to_subtract = (date.weekday() + 1) % 7
    return date - datetime.timedelta(days=days_to_subtract)

def build_bitmap(message, gap=1):
    # Build a horizontal bitmap (list of 7 strings) for the message.
    rows = [""] * 7
    first = True
    for ch in message:
        if not first:
            for r in range(7):
                rows[r] += "0" * gap
        first = False
        pattern = FONT.get(ch)
        if pattern is None:
            raise ValueError(f"No font pattern for character: {ch}")
        for r in range(7):
            rows[r] += pattern[r]
    return rows  # 7 strings; each string length = total columns

def parse_args():
    p = argparse.ArgumentParser(description="Draw 'Pizza!' on your GitHub contributions graph by creating backdated commits.")
    p.add_argument("--commits-per-pixel", type=int, default=4, help="How many commits to make for each 'on' pixel (default: 4). Increase for darker squares.")
    p.add_argument("--start-sunday", type=str, help="Explicit start Sunday (YYYY-MM-DD). If omitted the script aligns message to end at current week.")
    p.add_argument("--dry-run", action="store_true", help="Don't create commits; show which dates would be used.")
    return p.parse_args()

def make_commit_for_date(dt, commit_message):
    # dt is a datetime.date
    # set time to 12:00:00 UTC to avoid timezone/edge-day issues
    dt_str = dt.strftime("%Y-%m-%d 12:00:00 +0000")
    env = os.environ.copy()
    env["GIT_AUTHOR_DATE"] = dt_str
    env["GIT_COMMITTER_DATE"] = dt_str
    try:
        subprocess.run(["git", "commit", "--allow-empty", "-m", commit_message], check=True, env=env, stdout=subprocess.DEVNULL)
    except subprocess.CalledProcessError as e:
        print(f"git commit failed for date {dt_str}: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    args = parse_args()
    ensure_git_repo()

    bitmap = build_bitmap(MESSAGE, gap=1)
    total_cols = len(bitmap[0])
    print(f"Message '{MESSAGE}' => bitmap width {total_cols} weeks, height 7 days.")

    today = datetime.date.today()
    # We'll align the RIGHT edge of the bitmap to the current week (today's week).
    # Determine the Sunday of the current week
    current_week_sunday = get_sunday_of_week(today)
    # Start Sunday = current_week_sunday - (total_cols - 1) * 7 days
    start_sunday = current_week_sunday - datetime.timedelta(weeks=(total_cols - 1))
    if args.start_sunday:
        try:
            start_sunday = datetime.datetime.strptime(args.start_sunday, "%Y-%m-%d").date()
            # Ensure provided date is Sunday
            if start_sunday.weekday() != 6:
                print("Warning: provided --start-sunday is not a Sunday. Adjusting to nearest previous Sunday.")
                start_sunday = get_sunday_of_week(start_sunday)
        except ValueError:
            print("Invalid date format for --start-sunday. Use YYYY-MM-DD.", file=sys.stderr)
            sys.exit(1)

    print(f"Start Sunday (leftmost column): {start_sunday.isoformat()}")
    print(f"End week (rightmost) starts on: {start_sunday + datetime.timedelta(weeks=total_cols-1)} (current week Sunday: {current_week_sunday})")
    if args.dry_run:
        print("Dry run mode: listing all pixel dates that would receive commits.")
    commits_to_make = []
    for col in range(total_cols):
        week_start = start_sunday + datetime.timedelta(weeks=col)
        for row in range(7):  # 0..6 top->bottom (Sunday..Saturday)
            pixel_on = bitmap[row][col] == "1"
            if pixel_on:
                pixel_date = week_start + datetime.timedelta(days=row)
                commits_to_make.append(pixel_date)

    print(f"Total 'on' pixels: {len(commits_to_make)}. Commits per pixel: {args.commits_per_pixel}. Total commits to create: {len(commits_to_make) * args.commits_per_pixel}")

    if args.dry_run:
        for d in commits_to_make:
            print(d.isoformat())
        print("Done (dry run).")
        return

    confirm = input("Proceed to create the commits on the current branch? This will append commits to the branch. (y/N) ")
    if confirm.lower() != "y":
        print("Aborted.")
        return

    for d in commits_to_make:
        for i in range(args.commits_per_pixel):
            commit_msg = f"Pixel for Pizza! {d.isoformat()} (part {i+1}/{args.commits_per_pixel})"
            make_commit_for_date(d, commit_msg)
    print("All commits created. Push the branch to GitHub (git push) to see changes on your contributions graph.")

if __name__ == "__main__":
    main()