"""Phase 1, step 4: customer interviews, using The Mom Test method.

The agent writes the interview guide and outreach drafts. It never invents
interview answers. Sending outreach is an outbound action that needs founder
approval, and even then it is STUBBED (saved to the outbox for the founder to
send personally).
"""
from __future__ import annotations

import approval
from agents.base import Agent, StepResult, brief_summary, community_places, footer

MOM_TEST_RULES = [
    "Talk about their life and past behaviour, not about our idea.",
    "Ask about specifics in the past, not opinions about the future ('would you buy...?').",
    "Talk less, listen more. No pitching during the interview.",
    "Compliments and 'sounds great' are not evidence. Commitments (time, money, intro) are.",
]


class Interviewer(Agent):
    role = "interviewer"

    def run_step(self, candidate: dict, communities: dict) -> StepResult:
        fallback_questions = "\n".join(f"{i}. {q}" for i, q in enumerate([
            f"Tell me about the last time you dealt with {candidate.get('problem', 'this problem').rstrip('.').lower()}.",
            "What was the hardest part? Why?",
            "What did you try to solve it? What did that cost you in time or money?",
            "What don't you love about the things you tried?",
            "How are you handling it right now?",
            "Is there anyone else I should talk to about this?",
        ], 1))
        task = (f"Founder brief:\n{brief_summary(self.brief)}\nProduct idea: {candidate['title']}\nProblem: {candidate.get('problem', '')}\n\n"
                "Write a Mom Test interview guide: 7 numbered questions about the person's past behaviour with this problem "
                "(no hypothetical 'would you buy' questions, no pitching). Then 'What counts as a strong signal' with 3 bullets. Markdown, max 220 words.")
        guide = self.write(task, fallback_questions + "\n\nWhat counts as a strong signal:\n- They already spent money or hours on a workaround.\n"
                                                      "- They ask when they can get it, unprompted.\n- They offer an intro to someone else with the problem.",
                           max_tokens=600)
        name = self.brief.get("founder_name", "the founder")
        outreach = (f"Hi! I'm {name}. I'm researching how {self.brief.get('target_market', 'people')} deal with "
                    f"{candidate.get('problem', 'this problem').rstrip('.').lower()}. I'm not selling anything. "
                    "Could I ask you about your experience in a 15-minute call? Thank you either way.")
        places = ", ".join(community_places(communities)) or "communities the founder already belongs to"
        action = approval.request_action(self.run, "send", "customer interview outreach (5 people)",
                                         f"Personal message from {name} to 5 people found in {places}.",
                                         {"message": outreach}, agent=self.role)
        md = [f"# Phase 1, step 4: Customer interviews (Mom Test) for '{candidate['title']}'", "",
              "## Method", *[f"- {r}" for r in MOM_TEST_RULES], "", "## Interview guide", guide, "",
              "## Who to interview", f"- 5 to 8 people from: {places}.",
              "- Recruit only people who opted in. No scraping, no mass messages.", "",
              "## Outreach draft (written for the founder to send as themselves)", "", f"> {outreach}", "",
              f"Status: waiting for founder approval (action `{action['id']}`). Sending is STUBBED: after approval the message is "
              "saved to the outbox and the founder sends it personally.", "",
              "## Interview results", "",
              "No interviews have been run by the system. Results must come from real conversations: record them in the "
              "dashboard notes. The system does not simulate customers.", footer(self.model)]
        return self.result("interviews", "plan_customer_interviews", "\n".join(md), data={"outreach_action": action["id"]})
