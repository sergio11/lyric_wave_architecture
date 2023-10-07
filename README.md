# LyricWave: AI-Powered Music Generation Platform

LyricWave is a cutting-edge music generation platform that seamlessly fuses song lyrics with original melodies and synthetic vocals, resulting in personalized and enchanting MP3 and MIDI tracks. Leveraging the robust capabilities of Apache Airflow and the creative prowess of Magenta AI, LyricWave transforms mere text into fully-fledged musical compositions, offering a unique and captivating auditory experience.

<p align="center">
  <img src="https://img.shields.io/badge/flask-%23000.svg?style=for-the-badge&logo=flask&logoColor=white" />
  <img src="https://img.shields.io/badge/Apache%20Airflow-017CEE?style=for-the-badge&logo=Apache%20Airflow&logoColor=white" />
  <img src="https://img.shields.io/badge/gunicorn-%298729.svg?style=for-the-badge&logo=gunicorn&logoColor=white" />
  <img src="https://img.shields.io/badge/redis-%23DD0031.svg?style=for-the-badge&logo=redis&logoColor=white" />
  <img src="https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54" />
  <img src="https://img.shields.io/badge/postgres-%23316192.svg?style=for-the-badge&logo=postgresql&logoColor=white" />
  <img src="https://img.shields.io/badge/MongoDB-%234ea94b.svg?style=for-the-badge&logo=mongodb&logoColor=white" />
  <img src="https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white" />
</p>

## Features
- **Melody Crafting**: Harnessing the capabilities of Magenta AI, LyricWave crafts melodies that resonate with the sentiment and tone of song lyrics, producing intricate musical arrangements that complement the text's emotional content.

- **Voice Synthesis**: By employing innovative text-to-speech techniques, LyricWave generates synthetic vocal tracks that resonate with the song's lyrical essence, infusing the composition with expressive and realistic vocals.

- **Harmonious Fusion**: LyricWave masterfully combines the generated melodies and synthetic voices to produce harmonious MP3 tracks, culminating in an immersive listening experience that encapsulates both musical and lyrical dimensions.

- **Abstract Visuals**: In addition to its auditory allure, LyricWave generates captivating abstract images inspired by the song's lyrical content, providing a unique visual representation of the musical narrative.

- **MongoDB Integration**: LyricWave seamlessly integrates with MongoDB to store comprehensive details about the generated songs, including melodies, vocals, abstract images, and metadata.

- **Docker-Powered Workflow**: The project is encapsulated within a Docker Compose environment, streamlining the deployment and orchestration of the entire music generation pipeline.

## Technologies Used
- **Apache Airflow**: An extensible platform for orchestrating complex workflows, Airflow serves as the backbone for scheduling and managing the multi-step music generation process.

- **Magenta AI**: Developed by Google, Magenta AI facilitates creative musical composition and generation, allowing LyricWave to infuse songs with AI-crafted melodies.

- **Flask**: The Flask web framework powers the API component of LyricWave, enabling users to initiate and manage music generation tasks seamlessly.

- **MongoDB**: As a versatile NoSQL database, MongoDB stores and retrieves song data, including melodies, synthetic vocals, and abstract images, ensuring the seamless management of generated content.

- **Docker**: Employing Docker Compose, LyricWave encapsulates its components within containers, promoting consistency and portability across development and deployment environments.

## Project Structure
LyricFlow's project structure is organized as follows:

- `dags/`: Apache Airflow DAGs and custom operators for orchestrating the music generation pipeline.

- `operators/`: Custom Airflow operators for generating melodies, synthesizing voices, combining audio, and more.

- `api/`: A Flask-based API that facilitates the initiation of music generation tasks and audio streaming.

- `models/`: Contains pre-trained models and configurations utilized by Magenta AI for melody generation.

- `images/`: Stores abstract images generated from song lyrics, providing a unique visual representation of each composition.

- `requirements.txt`: Lists Python dependencies required for the project.

- `docker-compose.yml`: Configuration file for Docker Compose to set up the project environment.

## Getting Started
1. Clone this repository to your local machine.
2. Configure environment variables in `.env` to tailor the project settings to your requirements.
3. Execute `docker-compose up` to initiate the project within the Docker Compose environment.
4. Access the Airflow UI at `http://localhost:8080` to trigger and monitor music generation tasks.
5. Utilize the Flask API at `http://localhost:5000` for requesting music streaming and initiating the composition process.

## Contribution
Contributions to LyricWave are highly encouraged! If you're interested in adding new features, resolving bugs, or enhancing the project's functionality, please feel free to submit pull requests.

## License
This project is licensed under the [MIT License](LICENSE).
