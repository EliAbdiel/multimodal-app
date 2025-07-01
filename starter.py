import chainlit as cl


async def select_starters():
    """
    Returns a list of starter options for the chatbot interface.
    Each starter contains a label, message prompt, and associated icon.
    """
    return [
        cl.Starter(
            label="Ética IA Investigación",
            message="Busca información sobre la ética en la inteligencia artificial.",
            icon="/public/starters/search-globe.svg",
            ),
        cl.Starter(
            label="Genera una imagen",
            message="Genera un dibujo de un dragón volando.",
            icon="/public/starters/image-picture.svg",
            ),
        cl.Starter(
            label="Set Small Goals",
            message="Do you have any tips for staying motivated?",
            icon="/public/starters/write.svg",
            ),
        cl.Starter(
            label="Transcribe Youtube video",
            message="https://youtu.be/rwF-X5STYks?si=gXd7O8e7q5NpHm8h",
            icon="/public/starters/youtube.svg",
            ),
        cl.Starter(
            label="Aprende machine learning",
            message="Recomiéndame algunos recursos para aprender sobre machine learning",
            icon="/public/starters/human-learn.svg",
            )
        ]