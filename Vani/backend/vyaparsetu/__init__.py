"""VyaparSetu integration for the Vani chatbot.

Vani's intent understanding (LLM + deterministic fallback parser) is reused
unchanged. Only the *execution* layer is replaced: instead of Vani's in-memory
demo database, actions are carried out on the logged-in seller's real
VyaparSetu shop through the VyaparSetu backend API, using the seller's own
access token (so VyaparSetu's auth checks and Supabase RLS apply).
"""
