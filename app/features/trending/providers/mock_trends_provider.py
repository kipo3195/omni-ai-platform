from app.features.trending.trending_models import TrendingTopic
from app.features.trending.providers.provider import TrendingProvider


class MockTrendingProvider(TrendingProvider):

    async def fetch(self) -> list[TrendingTopic]:
        return [
            TrendingTopic(
                topic="두바이 초콜릿",
                category="food",
                summary="최근 두바이 초콜릿 디저트가 SNS에서 유행",
                keywords=["두바이 초콜릿", "디저트", "SNS"],
            ),
            TrendingTopic(
                topic="오늘 날씨",
                category="weather",
                summary="오늘의 날씨와 기온 이야기",
                keywords=["날씨", "기온", "비"],
            ),
            TrendingTopic(
                topic="점심 메뉴",
                category="food",
                summary="오늘 점심으로 먹기 좋은 메뉴",
                keywords=["점심", "메뉴", "맛집"],
            ),
            TrendingTopic(
                topic="저녁 메뉴",
                category="food",
                summary="오늘 저녁 식사 메뉴 이야기",
                keywords=["저녁", "메뉴", "식사"],
            ),
            TrendingTopic(
                topic="요즘 인기 음식",
                category="food",
                summary="최근 사람들이 많이 찾는 음식",
                keywords=["음식", "맛집", "인기"],
            ),
            TrendingTopic(
                topic="주말 계획",
                category="daily",
                summary="다가오는 주말에 할 만한 활동",
                keywords=["주말", "계획", "휴식"],
            ),
            TrendingTopic(
                topic="퇴근 후 계획",
                category="daily",
                summary="퇴근 후 무엇을 할지 이야기",
                keywords=["퇴근", "저녁", "일상"],
            ),
            TrendingTopic(
                topic="출근길 이야기",
                category="daily",
                summary="오늘 출근길에서 있었던 일",
                keywords=["출근", "교통", "아침"],
            ),
            TrendingTopic(
                topic="요즘 관심사",
                category="daily",
                summary="최근 관심을 가지고 있는 주제",
                keywords=["관심사", "취미", "최근"],
            ),
            TrendingTopic(
                topic="최근 본 영화",
                category="movie",
                summary="최근 재미있게 본 영화 이야기",
                keywords=["영화", "극장", "추천"],
            ),
            TrendingTopic(
                topic="요즘 인기 드라마",
                category="drama",
                summary="최근 화제가 되는 드라마",
                keywords=["드라마", "OTT", "인기"],
            ),
            TrendingTopic(
                topic="요즘 보는 유튜브",
                category="content",
                summary="최근 즐겨 보는 유튜브 콘텐츠",
                keywords=["유튜브", "영상", "콘텐츠"],
            ),
            TrendingTopic(
                topic="요즘 듣는 음악",
                category="music",
                summary="최근 자주 듣는 음악과 가수",
                keywords=["음악", "노래", "가수"],
            ),
            TrendingTopic(
                topic="새로 나온 노래",
                category="music",
                summary="최근 발표된 새로운 음악",
                keywords=["신곡", "음악", "플레이리스트"],
            ),
            TrendingTopic(
                topic="최근 읽은 책",
                category="book",
                summary="최근 읽거나 관심 있는 책",
                keywords=["책", "독서", "추천"],
            ),
            TrendingTopic(
                topic="여행 가고 싶은 곳",
                category="travel",
                summary="요즘 떠나고 싶은 여행지",
                keywords=["여행", "여행지", "휴가"],
            ),
            TrendingTopic(
                topic="국내 여행",
                category="travel",
                summary="가볍게 떠나기 좋은 국내 여행지",
                keywords=["국내여행", "주말", "여행지"],
            ),
            TrendingTopic(
                topic="해외 여행",
                category="travel",
                summary="가보고 싶은 해외 여행지",
                keywords=["해외여행", "휴가", "여행"],
            ),
            TrendingTopic(
                topic="운동 이야기",
                category="health",
                summary="최근 하고 있는 운동이나 운동 계획",
                keywords=["운동", "헬스", "건강"],
            ),
            TrendingTopic(
                topic="건강 관리",
                category="health",
                summary="평소 건강을 관리하는 방법",
                keywords=["건강", "생활습관", "관리"],
            ),
            TrendingTopic(
                topic="요즘 취미",
                category="hobby",
                summary="최근 즐기고 있는 취미 활동",
                keywords=["취미", "여가", "관심사"],
            ),
            TrendingTopic(
                topic="게임 이야기",
                category="game",
                summary="최근 즐겨 하는 게임",
                keywords=["게임", "신작", "취미"],
            ),
            TrendingTopic(
                topic="요즘 인기 게임",
                category="game",
                summary="최근 사람들이 많이 즐기는 게임",
                keywords=["게임", "인기", "신작"],
            ),
            TrendingTopic(
                topic="AI 이야기",
                category="technology",
                summary="최근 관심을 받고 있는 AI 기술",
                keywords=["AI", "인공지능", "기술"],
            ),
            TrendingTopic(
                topic="새로운 IT 기술",
                category="technology",
                summary="최근 등장한 새로운 IT 기술과 서비스",
                keywords=["IT", "기술", "서비스"],
            ),
            TrendingTopic(
                topic="스마트폰 이야기",
                category="technology",
                summary="최근 스마트폰이나 모바일 기기 이야기",
                keywords=["스마트폰", "모바일", "기기"],
            ),
            TrendingTopic(
                topic="회사 생활",
                category="work",
                summary="최근 회사에서 있었던 이야기",
                keywords=["회사", "직장", "업무"],
            ),
            TrendingTopic(
                topic="업무 스트레스",
                category="work",
                summary="일하면서 힘들거나 스트레스 받는 부분",
                keywords=["업무", "스트레스", "직장"],
            ),
            TrendingTopic(
                topic="휴가 계획",
                category="daily",
                summary="다가오는 휴가에 무엇을 할지 이야기",
                keywords=["휴가", "계획", "여행"],
            ),
            TrendingTopic(
                topic="최근 재미있었던 일",
                category="daily",
                summary="최근 일상에서 재미있었던 경험",
                keywords=["일상", "재미", "경험"],
            ),
        ]