# 트렌딩 주제 하나가 어떤 데이터 구조를 가지는지
from pydantic import BaseModel, Field

from datetime import datetime

class TrendingTopic(BaseModel):
    topic: str
    category: str
    summary: str
    #keywords: list[str] = []
    keywords: list[str] = Field(default_factory=list)

    # google trends 용
    search_volume: str | None = None
    started_at: datetime | None = None
    source: str = "google_trends"

    
    news_items: list[dict] = Field(default_factory=list)
    trend_context: str | None = None


# topic
class TopicEvaluation(BaseModel):
    topic: str

    generality: float = Field(ge=0.0, le=1.0)
    specificity: float = Field(ge=0.0, le=1.0)
    searchability: float = Field(ge=0.0, le=1.0)
    topic_quality: float = Field(ge=0.0, le=1.0)
    obvious_sensitivity: float = Field(ge=0.0, le=1.0)


class TopicEvaluationResult(BaseModel):
    evaluations: list[TopicEvaluation]

# topic + news 
class NewsContextEvaluation(BaseModel):
    topic: str
    trend_context: str

    generality: float = Field(ge=0.0, le=1.0)
    lightness: float = Field(ge=0.0, le=1.0)
    conversationality: float = Field(ge=0.0, le=1.0)
    sensitivity: float = Field(ge=0.0, le=1.0)
    specificity: float = Field(ge=0.0, le=1.0)
    smalltalk_fit: float = Field(ge=0.0, le=1.0)

    keep: bool
    reject_reason: str | None = None    

class NewsContextEvaluationResult(BaseModel):
    evaluations: list[NewsContextEvaluation]


# 서비스에서 최종적으로 사용할 데이터
class EvaluatedTrendingTopic(BaseModel):
    topic: str
    category: str | None = None
    summary: str | None = None
    keywords: list[str] = Field(default_factory=list)

    generality: float
    lightness: float
    conversationality: float
    sensitivity: float
    specificity: float
    smalltalk_fit: float
    
    score: float

    trend_context: str | None = None
    base_question: str | None = None


class TrendingBaseQuestion(BaseModel):
    topic: str
    question: str


class TrendingBaseQuestionResult(BaseModel):
    questions: list[TrendingBaseQuestion]
