FROM astral/uv:python3.12-bookworm-slim

WORKDIR /app 
ADD uv.lock pyproject.toml ./
RUN uv sync

COPY . .

EXPOSE 8000
CMD [ "uv", "run","python" ,"-m", "InaBot.main" ]