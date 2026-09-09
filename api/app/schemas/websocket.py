from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, StringConstraints, TypeAdapter

# A chat line, not a document. Matches the input's `maxLength` in the frontend,
# so the browser never reaches this limit and it stays purely defensive against
# clients that are not the browser.
MAX_MESSAGE_LENGTH = 500


class JoinFrame(BaseModel):
    type: Literal["join"]


class MessageFrame(BaseModel):
    type: Literal["message"]
    # Stripped first, so a message of nothing but spaces fails `min_length`
    # rather than being broadcast as an empty line.
    message: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True, min_length=1, max_length=MAX_MESSAGE_LENGTH
        ),
    ]


# Fields the client sends that the server derives for itself -- `username` and
# `timestamp` -- are dropped here, which is Pydantic's default for extras. They
# were already ignored; now that is enforced rather than merely intended.
ClientFrame = Annotated[Union[JoinFrame, MessageFrame], Field(discriminator="type")]

client_frame = TypeAdapter(ClientFrame)
