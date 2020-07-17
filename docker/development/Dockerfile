FROM python:3.6

RUN mkdir /elastinga

WORKDIR /elastinga

# Poetry version
ARG POETRY_VERSION=1.0.0a5

RUN curl -sSL https://raw.githubusercontent.com/sdispater/poetry/master/get-poetry.py -o get-poetry.py
RUN python get-poetry.py --preview --version ${POETRY_VERSION}
RUN rm get-poetry.py
RUN mkdir -p /root/.config/pypoetry/
RUN touch /root/.config/pypoetry/config.toml
ENV PATH="/root/.poetry/bin:$PATH"
RUN poetry config settings.virtualenvs.create false

COPY docker/development/wait-for-elastic.sh ./ 

COPY poetry.lock pyproject.toml ./

RUN poetry install --no-interaction --no-ansi

COPY . /elastinga

RUN poetry install



