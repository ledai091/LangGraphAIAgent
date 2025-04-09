from typing import TypedDict
from chains.binary_questions import BINARY_QUESTION_CHAIN
from chains.escalation_check import ESCALATION_CHECK_CHAIN
from chains.notice_extraction import NOTICE_PARSER_CHAIN, NoticeEmailExtract
from langgraph.graph import END, START, StateGraph
from pydantic import EmailStr
from utils.graph_utils import create_legal_ticket, send_escalation_email
from utils.logging_config import LOGGER

class GraphState(TypedDict):
    notice_message: str
    notice_email_extract: NoticeEmailExtract | None
    escalation_text_criteria: str
    escalation_dollar_criteria: str
    requires_escalation: bool
    escalation_emails: list[EmailStr] | None
    follow_ups: dict[str, bool] | None
    current_follow_up: str | None

workflow = StateGraph(GraphState)


def parse_notice_message_node(state: GraphState) -> GraphState:
    LOGGER.info("Parsing notice...")
    notice_email_extract = NOTICE_PARSER_CHAIN.invoke(
        {"message": state["notice_message"]}
    )

    state["notice_email_extract"] = notice_email_extract
    return state

def check_escalation_status_node(state: GraphState) -> GraphState:
    LOGGER.info("Determining escalation status...")
    text_check = ESCALATION_CHECK_CHAIN.invoke(
        {
            "escalation_criteria": state["escalation_text_criteria"],
            "message": state["notice_message"]
        }
    ).needs_escalation

    if (
        text_check
        or state["notice_email_extract"].max_potential_fine >= state["escalation_dollar_criteria"]
    ):
        state["requires_escalation"] = True
    else:
        state["requires_escalation"] = False
    return state

def send_escalation_email_node(state: GraphState) -> GraphState:
    send_escalation_email(
        state["notice_email_extract"],
        state["escalation_emails"],
    )
    return state

def create_legal_ticket_node(state: GraphState) -> GraphState:
    follow_up = create_legal_ticket(
        current_follow_ups=state.get("follow_ups"),
        notice_email_extract=state["notice_email_extract"]
    )
    state["current_follow_up"] = follow_up
    return state

def route_escalation_status_edge(state: GraphState) -> str:
    if state["requires_escalation"]:
        LOGGER.info("Escalation required")
        return "send_escalation_email"
    LOGGER.info("No escalation required")
    return "create_legal_ticket"

def answer_follow_up_question_node(state: GraphState) -> GraphState:
    if state["current_follow_up"]:
        question = state["current_follow_up"]
        answer = BINARY_QUESTION_CHAIN.invoke({"question": question})
        if state.get("follow_ups"):
            state["follow_ups"][state["current_follow_up"]] = answer
        else:
            state["follow_ups"] = {state["current_follow_up"]: answer}
    return state

def route_follow_up_edge(state: GraphState) -> str:
    if state["current_follow_up"]:
        return "answer_follow_up_question"
    return END

#making nodes
workflow.add_node("parse_notice_message", parse_notice_message_node)
workflow.add_node("check_escalation_status", check_escalation_status_node)
workflow.add_node("send_escalation_email", send_escalation_email_node)
workflow.add_node("create_legal_ticket", 
create_legal_ticket_node)
workflow.add_node("answer_follow_up_question", 
answer_follow_up_question_node)
#making edges
workflow.add_edge(START, "parse_notice_message")
workflow.add_edge("parse_notice_message", "check_escalation_status")
workflow.add_conditional_edges(
    "check_escalation_status",
    route_escalation_status_edge,
    {
        "send_escalation_email": "send_escalation_email",
        "create_legal_ticket": "create_legal_ticket",
    }
)
workflow.add_conditional_edges(
    "create_legal_ticket",
    route_follow_up_edge,
    {
        "answer_follow_up_question": "answer_follow_up_question",
        END: END,
    }
)

workflow.add_edge("send_escalation_email", "create_legal_ticket")
workflow.add_edge("answer_follow_up_question","create_legal_ticket")

NOTICE_EXTRACTION_GRAPH = workflow.compile()


