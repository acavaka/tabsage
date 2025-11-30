"""Pydantic models for TabSage messages"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class IngestPayload(BaseModel):
    """Input payload for Ingest Agent"""
    raw_text: str = Field(..., description="Raw text to process")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    session_id: str = Field(..., description="Session identifier")
    episode_id: Optional[str] = Field(None, description="Episode identifier")


class IngestResponse(BaseModel):
    """Output response from Ingest Agent"""
    title: str = Field(..., description="Extracted or generated title")
    language: str = Field(..., description="Detected language code (e.g., 'ru', 'en')")
    cleaned_text: str = Field(..., description="Cleaned text without ads/markers")
    summary: str = Field(..., description="Short summary (1-2 sentences)")
    chunks: List[str] = Field(..., max_length=5, description="Text chunks (max 5)")
    session_id: str = Field(..., description="Session identifier")
    episode_id: Optional[str] = Field(None, description="Episode identifier")


# KG Builder Schemas

class Entity(BaseModel):
    """Entity extracted from text"""
    type: str = Field(..., description="Entity type (PERSON, ORGANIZATION, LOCATION, etc.)")
    canonical_name: str = Field(..., description="Canonical name of the entity")
    aliases: List[str] = Field(default_factory=list, description="Alternative names/aliases")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0-1)")


class Relation(BaseModel):
    """Relation between entities"""
    subject: str = Field(..., description="Subject entity (canonical name)")
    predicate: str = Field(..., description="Relation type (WORKS_FOR, LOCATED_IN, etc.)")
    object: str = Field(..., description="Object entity (canonical name)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0-1)")


class KGChunkExtraction(BaseModel):
    """Extracted entities and relations from a single chunk"""
    entities: List[Entity] = Field(default_factory=list, description="Extracted entities")
    relations: List[Relation] = Field(default_factory=list, description="Extracted relations")
    chunk_text: str = Field(..., description="Original chunk text")
    chunk_index: int = Field(..., description="Index of chunk in original document")


class KGBuilderPayload(BaseModel):
    """Input payload for KG Builder Agent"""
    chunks: List[str] = Field(..., description="Text chunks from Ingest Agent")
    title: str = Field(..., description="Document title")
    language: str = Field(..., description="Language code")
    session_id: str = Field(..., description="Session identifier")
    episode_id: Optional[str] = Field(None, description="Episode identifier")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class KGBuilderResponse(BaseModel):
    """Output response from KG Builder Agent"""
    entities: List[Entity] = Field(default_factory=list, description="All extracted entities")
    relations: List[Relation] = Field(default_factory=list, description="All extracted relations")
    chunk_extractions: List[KGChunkExtraction] = Field(default_factory=list, description="Per-chunk extractions")
    session_id: str = Field(..., description="Session identifier")
    episode_id: Optional[str] = Field(None, description="Episode identifier")
    graph_updated: bool = Field(default=False, description="Whether graph was successfully updated")


# Topic Discovery Schemas

class Topic(BaseModel):
    """Topic for podcast episode"""
    title: str = Field(..., description="Topic title")
    why_it_matters: str = Field(..., description="Why this topic matters (1-2 sentences)")
    seed_nodes: List[str] = Field(default_factory=list, description="List of KG node IDs")
    difficulty: str = Field(..., description="Difficulty level: low/medium/high")
    estimated_length_minutes: int = Field(..., ge=1, description="Estimated episode length in minutes")


class TopicDiscoveryPayload(BaseModel):
    """Input payload for Topic Discovery Agent"""
    session_id: str = Field(..., description="Session identifier")
    episode_id: Optional[str] = Field(None, description="Episode identifier")
    max_topics: int = Field(default=10, ge=1, le=10, description="Maximum number of topics to discover")
    graph_snapshot: Optional[Dict[str, Any]] = Field(None, description="Graph snapshot (if not provided, will be fetched)")


class TopicDiscoveryResponse(BaseModel):
    """Output response from Topic Discovery Agent"""
    topics: List[Topic] = Field(default_factory=list, description="Discovered topics")
    session_id: str = Field(..., description="Session identifier")
    episode_id: Optional[str] = Field(None, description="Episode identifier")
    graph_stats: Dict[str, Any] = Field(default_factory=dict, description="Graph statistics at discovery time")


# Scriptwriter Schemas

class ScriptSegment(BaseModel):
    """Segment of podcast script"""
    segment_type: str = Field(..., description="Segment type: intro, hook, body, interview, conclusion")
    timing: str = Field(..., description="Timing information (e.g., '0:00-2:30')")
    content: str = Field(..., description="Script content for this segment")
    key_facts: List[str] = Field(default_factory=list, description="Key facts to mention")
    quotes: List[str] = Field(default_factory=list, description="Quotes to include")
    questions: List[str] = Field(default_factory=list, description="Questions to ask")
    kg_references: List[str] = Field(default_factory=list, description="References to KG nodes")


class ScriptwriterPayload(BaseModel):
    """Input payload for Scriptwriter Agent"""
    topic: Topic = Field(..., description="Topic for the episode")
    target_audience: str = Field(..., description="Target audience description")
    format: str = Field(default="informative", description="Format: informative, interview, storytelling")
    session_id: str = Field(..., description="Session identifier")
    episode_id: Optional[str] = Field(None, description="Episode identifier")


class ScriptwriterResponse(BaseModel):
    """Output response from Scriptwriter Agent"""
    segments: List[ScriptSegment] = Field(default_factory=list, description="Script segments")
    full_script: str = Field(..., description="Full script text")
    total_estimated_minutes: int = Field(..., description="Total estimated duration")
    session_id: str = Field(..., description="Session identifier")
    episode_id: Optional[str] = Field(None, description="Episode identifier")


# Guest/Persona Agent Schemas

class GuestResponse(BaseModel):
    """Response from Guest/Persona Agent"""
    short_answer: str = Field(..., description="Short answer (1-2 sentences)")
    detailed_answer: str = Field(..., description="Detailed answer")
    kg_references: List[str] = Field(default_factory=list, description="References to KG nodes")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence level (0-1)")


# Audio Producer Schemas

class TTSPrompt(BaseModel):
    """TTS prompt for a segment"""
    segment_id: str = Field(..., description="Segment identifier")
    ssml: Optional[str] = Field(None, description="SSML markup")
    text: str = Field(..., description="Text to synthesize")
    voice: str = Field(default="default", description="Voice to use")
    speed: float = Field(default=1.0, description="Speech speed multiplier")
    tone: str = Field(default="neutral", description="Tone: neutral, excited, calm, etc.")


class AudioRecommendation(BaseModel):
    """Audio production recommendations"""
    music_track: Optional[str] = Field(None, description="Recommended music track")
    sound_effects: List[str] = Field(default_factory=list, description="Sound effects to add")
    target_lufs: float = Field(default=-16.0, description="Target loudness in LUFS")
    post_processing: List[str] = Field(default_factory=list, description="Post-processing steps")


class AudioProducerPayload(BaseModel):
    """Input payload for Audio Producer Agent"""
    segments: List[ScriptSegment] = Field(..., description="Script segments")
    full_script: str = Field(..., description="Full script text")
    session_id: str = Field(..., description="Session identifier")
    episode_id: Optional[str] = Field(None, description="Episode identifier")


class AudioProducerResponse(BaseModel):
    """Output response from Audio Producer Agent"""
    tts_prompts: List[TTSPrompt] = Field(default_factory=list, description="TTS prompts for segments")
    recommendations: AudioRecommendation = Field(..., description="Audio recommendations")
    session_id: str = Field(..., description="Session identifier")
    episode_id: Optional[str] = Field(None, description="Episode identifier")


# Publisher Schemas

class PublicationMetadata(BaseModel):
    """Metadata for podcast publication"""
    title: str = Field(..., description="Episode title")
    description: str = Field(..., description="Episode description")
    tags: List[str] = Field(default_factory=list, description="Tags for discovery")
    transcript: str = Field(..., description="Full transcript")
    duration_minutes: int = Field(..., description="Episode duration")


class PublisherPayload(BaseModel):
    """Input payload for Publisher Agent"""
    script: ScriptwriterResponse = Field(..., description="Script to publish")
    audio_file_path: Optional[str] = Field(None, description="Path to audio file (if available)")
    session_id: str = Field(..., description="Session identifier")
    episode_id: Optional[str] = Field(None, description="Episode identifier")


class PublisherResponse(BaseModel):
    """Output response from Publisher Agent"""
    published: bool = Field(..., description="Whether publication was successful")
    publication_urls: Dict[str, str] = Field(default_factory=dict, description="URLs where published")
    metadata: PublicationMetadata = Field(..., description="Publication metadata")
    session_id: str = Field(..., description="Session identifier")
    episode_id: Optional[str] = Field(None, description="Episode identifier")


# Evaluator Schemas

class TextEvaluation(BaseModel):
    """Text evaluation metrics"""
    factuality: float = Field(..., ge=0.0, le=1.0, description="Factuality score (0-1)")
    coherence: float = Field(..., ge=0.0, le=1.0, description="Coherence score (0-1)")
    relevance: float = Field(..., ge=0.0, le=1.0, description="Relevance score (0-1)")
    hallucination_notes: str = Field(default="", description="Notes about hallucinations")
    explanation: str = Field(default="", description="Short explanation")


class AudioEvaluation(BaseModel):
    """Audio evaluation metrics"""
    snr: float = Field(..., description="Signal-to-noise ratio in dB")
    lufs: float = Field(..., description="Loudness in LUFS")
    clipping: bool = Field(..., description="Whether clipping detected")
    perceived_quality: int = Field(..., ge=1, le=5, description="Perceived quality (1-5)")
    suggestions: str = Field(default="", description="Improvement suggestions")


class EvaluatorPayload(BaseModel):
    """Input payload for Evaluator Agent"""
    text: Optional[str] = Field(None, description="Text to evaluate")
    audio_file_path: Optional[str] = Field(None, description="Audio file path to evaluate")
    audio_metrics: Optional[Dict[str, Any]] = Field(None, description="Pre-computed audio metrics")
    session_id: str = Field(..., description="Session identifier")
    episode_id: Optional[str] = Field(None, description="Episode identifier")


class EvaluatorResponse(BaseModel):
    """Output response from Evaluator Agent"""
    text_evaluation: Optional[TextEvaluation] = Field(None, description="Text evaluation (if text provided)")
    audio_evaluation: Optional[AudioEvaluation] = Field(None, description="Audio evaluation (if audio provided)")
    session_id: str = Field(..., description="Session identifier")
    episode_id: Optional[str] = Field(None, description="Episode identifier")


# Editor Agent Schemas

class EditorReview(BaseModel):
    """Human review feedback"""
    approved: bool = Field(..., description="Whether content is approved")
    feedback: str = Field(default="", description="Feedback/edits from human")
    changes_requested: List[str] = Field(default_factory=list, description="List of requested changes")


class EditorPayload(BaseModel):
    """Input payload for Editor Agent"""
    script: ScriptwriterResponse = Field(..., description="Script to review")
    audio_metadata: Optional[Dict[str, Any]] = Field(None, description="Audio metadata (if available)")
    session_id: str = Field(..., description="Session identifier")
    episode_id: Optional[str] = Field(None, description="Episode identifier")


class EditorResponse(BaseModel):
    """Output response from Editor Agent"""
    approved: bool = Field(..., description="Whether content was approved")
    review: Optional[EditorReview] = Field(None, description="Human review feedback")
    revised_script: Optional[ScriptwriterResponse] = Field(None, description="Revised script (if changes were made)")
    session_id: str = Field(..., description="Session identifier")
    episode_id: Optional[str] = Field(None, description="Episode identifier")

