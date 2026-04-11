# Metadata Schema

## Required Fields
- title
- genre
- theme
- audience
- reading_level
- rationale
- moral

## Optional Fields
- author
- tone
- structure
- keywords
- source_path

## Field Definitions
- title: the book name or a stable fallback label.
- genre: the broad story category.
- theme: the main idea or lesson topic.
- audience: the intended reader group.
- reading_level: easy, middle, or advanced.
- rationale: a short explanation for the chosen metadata.
- moral: the main lesson or takeaway.

## Output Rules
- Use lowercase keys when returning JSON.
- Keep values concise and consistent.
- If a field is not known, say "unknown".
- Do not produce competing labels for the same property.

## Example Record
```json
{
  "title": "The Ant and the Grasshopper",
  "genre": "fable",
  "theme": "responsibility and preparation",
  "audience": "children",
  "reading_level": "easy",
  "rationale": "Animal characters and a direct lesson make this a classic fable.",
  "moral": "Plan ahead and work steadily before difficult times arrive."
}
```