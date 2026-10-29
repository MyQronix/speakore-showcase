# Simulated conversations

**Why this exists.** A phone's screen recording only captures the sound the phone plays. While SpeaKore holds the
microphone, your own voice never ends up in the recording. So to show both sides of a real conversation on video, we
simulated the two people instead: John speaks English, Lucía speaks Spanish.

**What is real.** Their voices are pre-recorded WAV files in `voices/`. Everything after that is the live SpeaKore
server on Nebius AI Cloud: speech recognition, translation with NVIDIA Nemotron on Nebius Token Factory, and the spoken
translation. Nothing is mocked; only the speakers are simulated.

| Mode | What happens |
|---|---|
| `street` | John and Lucía each connect as their own phone and pair up, like two people in the street |
| `table` | One phone in the middle with two seats, like two people at a table |

```bash
pip install httpx websockets numpy
export SPEAKORE_JURY_CODE=...     # judges receive this code privately
python simulate_conversation.py street
python simulate_conversation.py table
```

Each run writes a WAV file (every original sentence followed by the translation the other person heard) and an `.srt`
subtitle file, and prints the time from the end of each sentence to the start of the spoken translation.

**Example run (29 October 2026, server in France):**

| Who | Says | The other hears | Time |
|---|---|---|---|
| John | Shall we play one more round before dinner? | ¿Jugamos una ronda más antes de la cena? | 1.9 s |
| Lucía | Sí, claro, pero la cena es a las nueve y media. | Yes, sure, but dinner is at 9:30. | 0.9 s |
| John | Perfect. Lucía, it is your turn to shuffle the cards. | Perfecto. Lucía, es tu turno de barajar las cartas. | 0.5 s |
| Lucía | Vale, pero esta vez no me ganas, te lo prometo. | Okay, but this time you won't beat me—I promise. | 0.9 s |
