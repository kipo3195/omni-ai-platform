# 실행 순서만 정의

from langgraph.graph import END, START, StateGraph

from app.features.conversation_start.nodes.generate_recent_candidates import (
    generate_recent_candidates
)
from app.features.conversation_start.nodes.generate_trending_candidates import (
    create_generate_trending_candidates_node
)
from app.features.conversation_start.nodes.select_result import (
    select_result
)

from app.features.conversation_start.nodes.load_trending_context import (
    create_load_trending_context_node,
)

from app.features.trending.trending_service import TrendingService

from app.features.conversation_start.nodes.analyze_recent_context import (
    analyze_recent_context
)

from app.features.conversation_start.conversation_start_schemas import SuggestionType
from app.features.conversation_start.conversation_start_state import ConversationStartState

# 요청한 state에 따른 분기처리 
def route_suggestion(
    state: ConversationStartState,
) -> str:

    if state["suggestion_type"] == SuggestionType.RECENT_CONTEXT:
        return "recent"

    return "trending"

def create_conversation_start_graph(
    trending_service: TrendingService,
):
    
    # 변경할 state, 운반할 데이터 규격
    builder = StateGraph(ConversationStartState)
    # ----------- 여기까지는 아직 실행할 노드가 하나도 없는 빈 그래프

    # 어떤 node에서 어떤 state를 처리할 것인가
    # 실제로 실행 가능한 노드를 그래프에 등록
    builder.add_node(
        "generate_recent_candidates",
        generate_recent_candidates,
    )

    builder.add_node(
        "generate_trending_candidates",
        create_generate_trending_candidates_node(),
    )

    builder.add_node(
        "select_result",
        select_result,
    )

    builder.add_node(
        "load_trending_context",
        create_load_trending_context_node(trending_service),
    )

    builder.add_node(
    "analyze_recent_context",
        analyze_recent_context,
    )

    # START, END는 LangGraph에서 미리 제공하는 특별한 노드라서 따로 add_node() 할 필요 없음.   
    # 현재 Node 실행 결과(State)를 보고 다음에 갈 Node를 조건에 따라 선택하는 기능
    builder.add_conditional_edges(
      START,
        route_suggestion,
        {
            "recent": "analyze_recent_context",
            "trending": "load_trending_context",
        },
    )

     # 등록된 노드들 사이의 이동 경로를 연결

    builder.add_edge(
        "analyze_recent_context",
        "generate_recent_candidates",
    )

    builder.add_edge(
        "generate_recent_candidates",
        "select_result",
    )

    builder.add_edge(
        "load_trending_context",
        "generate_trending_candidates",
    )
   
    builder.add_edge(
        "generate_trending_candidates",
        "select_result",
    )

    # START, END는 LangGraph에서 미리 제공하는 특별한 노드라서 따로 add_node() 할 필요 없음.
    builder.add_edge(
        "select_result",
        END,
    )

    return builder.compile()
