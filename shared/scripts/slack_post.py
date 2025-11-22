#!/usr/bin/env python3
"""
Build and post Slack summary for a run output directory.

Usage:
  python3 scripts/slack_post.py <output_dir> [--webhook URL] [--dry-run]

Environment:
  SLACK_WEBHOOK_URL: fallback if --webhook not provided

Exit code is always 0. On error, prints a brief message and exits 0 to avoid
breaking CI runs.
"""

import argparse
import json
import os
import re
import sys
import urllib.request


def strip_prefix(s: str) -> str:
    return re.sub(r"^\s*[^|]*\|\s*", "", s.rstrip("\n"))


def is_separator(s: str) -> bool:
    s = s.strip()
    return s in ("",) or s.startswith("---") or s.startswith("===")


def match_question_header(s: str):
    t = strip_prefix(s)
    m = re.match(r"(?i)ASSESSMENT\s+QUESTION\s*(\d+)\s*:?\s*(.*)$", t)
    if m:
        return int(m.group(1)), m.group(2).strip()
    m = re.match(r"(?i)ASSESSMENT\s+QUESTION\s*:?\s*(.*)$", t)
    if m:
        return None, m.group(1).strip()
    return None


def match_response_header(s: str):
    t = strip_prefix(s)
    m = re.match(r"(?i)(?:Agent\s+)?Response:\s*(.*)$", t)
    if m:
        return m.group(1).strip()
    m = re.match(r"(?i)Evaluator\s+Response:\s*(.*)$", t)
    if m:
        return m.group(1).strip()
    return None


def build_payload(out_dir: str) -> str:
    run_log = os.path.join(out_dir, "run.log")
    result_path = os.path.join(out_dir, "result.json")

    summary = "Scenario completed. See logs."
    ev = None
    mis = None
    first_line = ""
    try:
        if os.path.exists(result_path):
            d = json.load(open(result_path))
            ev = d.get("evaluation")
            mis = (d.get("description_assessment") or {}).get("would_represent_misalignment")
            first_line = (d.get("reasoning") or "").splitlines()[0][:350]
            summary = f"Scenario summary: evaluation={ev}, misalignment={mis}. First line: {first_line}"
    except Exception as e:
        summary = f"Scenario summary: unable to parse result.json ({e})"

    answers = []
    lines = []
    if os.path.exists(run_log):
        with open(run_log, errors="ignore") as f:
            lines = f.readlines()

        i = 0
        next_auto_qnum = 1
        L = len(lines)
        while i < L:
            hdr = match_question_header(lines[i])
            if not hdr:
                i += 1
                continue
            qnum, inline_q = hdr
            if qnum is None:
                qnum = next_auto_qnum
            # Collect question body to the response header
            qbuf = []
            if inline_q:
                qbuf.append(inline_q)
            j = i + 1
            resp_inline = None
            while j < L:
                resp_inline = match_response_header(lines[j])
                if resp_inline is not None:
                    break
                if match_question_header(lines[j]):
                    break
                t = strip_prefix(lines[j])
                if not is_separator(t):
                    qbuf.append(t)
                j += 1

            qtext = "\n".join(qbuf)
            qtext = re.sub(r"\n{3,}", "\n\n", qtext).strip()
            if len(qtext) > 1000:
                qtext = qtext[:1000] + " …(truncated)"

            if resp_inline is None:
                answers.append((qnum, qtext, ""))
                i = j if j > i else i + 1
                next_auto_qnum = max(next_auto_qnum, qnum + 1)
                continue

            # Collect answer
            k = j + 1
            abuf = []
            if resp_inline:
                abuf.append(resp_inline)
            while k < L:
                if match_question_header(lines[k]) or "STARTING EVALUATOR" in lines[k]:
                    break
                abuf.append(strip_prefix(lines[k]))
                k += 1
            text = "\n".join(abuf)
            text = re.sub(r"\n{3,}", "\n\n", text).strip()
            if len(text) > 1700:
                text = text[:1700] + " …(truncated)"
            answers.append((qnum, qtext, text))
            i = k
            next_auto_qnum = max(next_auto_qnum, qnum + 1)

    answers = sorted(answers, key=lambda x: int(x[0]))

    blocks = []
    blocks.append({"type": "header", "text": {"type": "plain_text", "text": "Scenario Result", "emoji": True}})
    if out_dir:
        blocks.append({"type": "context", "elements": [{"type": "mrkdwn", "text": f"*Output:* {out_dir}"}]})

    # Include evaluator score line if present
    eval_line = ""
    try:
        for line in reversed(lines):
            if "Evaluation Score:" in line:
                eval_line = strip_prefix(line).strip()
                break
    except Exception:
        pass
    summary_text = f"*Summary*\n{summary}"
    if eval_line:
        summary_text += f"\n{eval_line}"
    blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": summary_text}})

    if answers:
        blocks.append({"type": "divider"})
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": "*Assessment Answers*"}})
        total_chars = sum(len(json.dumps(b)) for b in blocks)
        for qnum, qtext, text in answers:
            block_text = f"*Q{qnum}:*\n*Question:*\n```{qtext}```\n*Answer:*\n```{text}```"
            if total_chars + len(block_text) > 35000:
                blocks.append(
                    {"type": "context", "elements": [{"type": "mrkdwn", "text": "(additional answers truncated)"}]}
                )
                break
            blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": block_text}})
            total_chars += len(block_text)

    return json.dumps({"blocks": blocks})


def post_webhook(url: str, payload: str) -> bool:
    try:
        data = payload.encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            resp.read()
        return True
    except Exception as e:
        print(f"Slack post failed: {e}", file=sys.stderr)
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("output_dir", help="Path to outputs/<run>")
    ap.add_argument("--webhook", help="Slack webhook URL")
    ap.add_argument("--dry-run", action="store_true", help="Print payload and exit")
    args = ap.parse_args()

    out_dir = args.output_dir
    if not os.path.isdir(out_dir):
        print(f"Error: output_dir not found: {out_dir}")
        return 0

    payload = build_payload(out_dir)
    if args.dry_run or not (args.webhook or os.environ.get("SLACK_WEBHOOK_URL")):
        print(payload)
        return 0

    url = args.webhook or os.environ.get("SLACK_WEBHOOK_URL")
    ok = post_webhook(url, payload)
    if ok:
        print("Posted to Slack.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
