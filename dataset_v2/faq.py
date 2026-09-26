"""D22: definitions, FAQ and worked examples. Lowest precedence. Several examples deliberately use the base schedule value that was current when they were
written and are therefore stale after a later circular; they are labelled non-binding. They are retrieval distractors and are never cited by the ground truth."""
from __future__ import annotations
from . import world as W
from .policy_text import C, m


def d22():
    ex = []
    def E(n, when, title, body): ex.append(C(f"FAQ-EX-{n}", f"Worked example {n}: {title}", f"Prepared {when}. Non-binding illustration; figures reflect the schedule at the time of writing and a later circular may have changed them. {body}"))
    h = W.HOTEL.base
    E(1, "January 2025", "Tokyo hotel for grade G4", f"A grade G4 employee stays 3 nights in Tokyo in 2025 and is billed JPY {3 * 34000:,} in total. The nightly rate is JPY 34,000, which equals the 2025 ceiling of JPY {h[('JP-TOKYO', 'G4-G5')][2025]:,} for the band G4-G5, so the hotel is within the ceiling.")
    E(2, "February 2025", "Singapore client dinner", f"Four people, of whom two are external, dine in Singapore in 2025 and are billed SGD 470. Spend per attendee is SGD 117.50 against a ceiling of SGD {W.CLIENT_MEAL.base['SG'][2025]}, so the meal is within the ceiling.")
    E(3, "March 2025", "India employee meal", f"Three employees in India share a meal costing INR 6,300 in 2025. Spend per person is INR 2,100 against a ceiling of INR {W.EMP_MEAL.base['IN'][2025]:,}. The meal is above the ceiling.")
    E(4, "January 2026", "Japan client meal", f"Five people dine in Japan in 2026 and are billed JPY 64,000. Spend per attendee is JPY 12,800 against a ceiling of JPY {W.CLIENT_MEAL.base['JP'][2026]:,}. The meal is within the ceiling.")
    E(5, "January 2026", "Singapore gift", f"A single gift worth SGD 118 is bought for a client contact in Singapore in 2026. The per-gift ceiling is SGD {W.GIFT.base['SG'][2026]}, so the gift is within the ceiling.")
    E(6, "February 2026", "Bengaluru hotel", f"A grade G6 employee in Bengaluru in 2026 pays INR 18,400 per night. The 2026 ceiling for the band G6-G7 in the Tier-1 row is INR {h[('IN-T1', 'G6-G7')][2026]:,}. The hotel is within the ceiling.")
    E(7, "December 2024", "Late submission", "A claim for a transaction on 3 December 2024 is submitted on 20 January 2025. The claim is 48 days old. Under the 2024 policy the window is 60 days, so the claim is on time.")
    E(8, "May 2025", "Late submission in 2025", "A claim for a transaction on 1 April 2025 is submitted on 25 June 2025. The claim is 85 days old and falls in the manager-approval tier.")
    E(9, "June 2025", "Conference uplift", f"A registered attendee stays at the official partner hotel in Osaka in 2025. The base ceiling for the band G4-G5 is JPY {h[('JP-MAJOR', 'G4-G5')][2025]:,}; with the 2025 uplift of {W.CONF_UPLIFT[2025]} percent the ceiling is JPY {int(h[('JP-MAJOR', 'G4-G5')][2025] * 1.2):,}.")
    E(10, "April 2025", "Approval threshold and FX", "An expense of INR 30,000 is incurred in India in a month when one INR is worth 0.0160 SGD. The SGD equivalent is SGD 480, which is below the global manager threshold, so no approval is required under the global policy.")
    E(11, "August 2025", "Software subscription", "A subscription of SGD 640 for a design tool requires manager approval under the software policy.")
    E(12, "November 2024", "Split purchase", "Two purchases of SGD 260 and SGD 250 at the same merchant on the same day for the same project total SGD 510. The combined amount is above the manager threshold.")
    E(13, "September 2025", "Telecom", "An employee in Japan claims JPY 6,000 for mobile data in a month in which JPY 4,500 has already been reimbursed. The total is JPY 10,500.")
    E(14, "February 2026", "Training ceiling", "A grade G5 employee has been reimbursed SGD 3,000 of external training in 2026 and claims a further SGD 900. The cumulative total is SGD 3,900.")
    faqs = [
        ("Who decides when two policies appear to conflict?", "The order of precedence in the global policy decides. Where precedence cannot be determined from published text the claim goes to Finance."),
        ("Does an employee explanation ever replace a system record?", "No. Where an authoritative record exists it controls. The explanation is used to understand the purpose of the expense."),
        ("What is a discretionary expense?", "An expense the employee chose to incur within business purpose, as opposed to a mandatory statutory charge or a cost fixed by contract."),
        ("Are taxes included in the amount tested against a ceiling?", "The total on the bill, including taxes and mandatory service charges, is tested, unless the category policy says the nightly rate or the pre-tip bill is used."),
        ("Can a claim be partly approved?", "A claim receives one disposition. Where the business portion cannot be separated, or the claim exceeds a computed amount, the claim is returned or rejected as the category policy states."),
        ("What happens when a cited exception cannot be found?", "The reviewer requests the correct reference from the employee."),
        ("Is a manager approval given after the expense valid?", "Approval validity is tested against the transaction date and the approval status, as the approval policy sets out."),
        ("Can a manager delegate approval while travelling?", "Yes, through a recorded delegation with a validity period and a limit, as the approval policy describes."),
        ("How are recurring charges treated?", "A repeat that follows the normal interval and the same purpose is not a duplicate; the controls policy sets the interval."),
        ("Do regional addenda apply to an employee based in one country who spends in another?", "The addendum of the country where the expense was incurred applies."),
        ("Which document is authoritative for grade?", "The employee profile record, not the claim."),
        ("Are tips reimbursable in every country?", "The meals policy and the regional addendum decide. In some countries gratuities are not customary."),
        ("What is the difference between a gift and hospitality?", "A gift is given to keep; hospitality is a shared event such as a meal."),
        ("Can a project charge to another project's budget?", "A child project charges the cost centre of its parent project, as the budget policy describes."),
        ("Where do I find a superseded value?", "The historical schedules list the base values by year; circulars supersede them from their effective dates."),
    ]
    defs = [
        C("DEF-1.1", "Calendar day", "Deadlines are counted in calendar days including weekends and public holidays, from the transaction date to the submission date."),
        C("DEF-1.2", "External attendee", "A person who is not an employee of the company or its subsidiaries."),
        C("DEF-1.3", "Approver level", "The seniority of an approver: MANAGER, DIRECTOR or FINANCE, in ascending order."),
        C("DEF-1.4", "Cost centre and project", "A cost centre is a budget holder. A project is a work order charged to a cost centre, optionally under a parent project."),
        C("DEF-1.5", "Grade band", "Grades are grouped into bands used in ceiling tables."),
        C("DEF-1.6", "Nightly rate", "The total accommodation charge divided by the number of nights."),
    ]
    faq_clauses = [C(f"FAQ-1.{i + 1}", f"Question {i + 1}", f"Q: {q}\n\nA: {a}") for i, (q, a) in enumerate(faqs)]
    return dict(id="D22", key="FAQ", title="Definitions, Frequently Asked Questions and Worked Examples", region="GLOBAL", eff=("2024-01-01", "2099-12-31"), category="faq", rank=7, clauses=defs + faq_clauses + ex)
