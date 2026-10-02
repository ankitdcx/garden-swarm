"""Garden-native advisory IR. Parsing never grants execution authority."""
from .dsl import GardenError, Document, Record, parse, dumps
__all__ = ["GardenError", "Document", "Record", "parse", "dumps"]
