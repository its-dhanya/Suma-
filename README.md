<div align="center">

# **SUMA**

> *Your Smart Note-Taking Assistant*

![last commit](https://img.shields.io/github/last-commit/its-dhanya/suma-)
![javascript](https://img.shields.io/badge/javascript-55.7%25-blue)
![languages](https://img.shields.io/badge/languages-5-inactive)

---

## 🔧 Built with the tools and technologies:

<p align="center">
  <img src="https://img.shields.io/badge/JSON-black?logo=json&logoColor=white" />
  <img src="https://img.shields.io/badge/Rust-black?logo=rust&logoColor=white" />
  <img src="https://img.shields.io/badge/npm-red?logo=npm&logoColor=white" />
  <img src="https://img.shields.io/badge/TOML-brown?logo=toml&logoColor=white" />
  <img src="https://img.shields.io/badge/JavaScript-yellow?logo=javascript&logoColor=black" />
  <br />
  <img src="https://img.shields.io/badge/Tauri-00B4AB?logo=tauri&logoColor=white" />
  <img src="https://img.shields.io/badge/React-61DAFB?logo=react&logoColor=black" />
  <img src="https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Vite-646CFF?logo=vite&logoColor=white" />

</p>

</div>

# Suma

Suma is your smart note-taking assistant that transforms lectures and meetings into clear, concise, and actionable summaries. By leveraging advanced AI-driven transcription and summarization techniques, Suma makes document retrieval and revision effortless.

## Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Repository Information](#repository-information)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
  - [Front-End Setup](#front-end-setup)
  - [Back-End Setup](#back-end-setup)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
  - [Development](#development)
- [UI Previews](#ui-previews)
- [Troubleshooting](#troubleshooting)

## Overview
Suma leverages state-of-the-art AI to convert spoken content into detailed transcripts and streamlined summaries. Whether it's a lecture or a meeting, Suma helps you focus on what matters most by distilling essential concepts and actionable takeaways.

## Features
- **Audio Recording & Upload**: Record lectures directly or upload YouTube video links to automatically fetch transcripts.
- **Accurate Transcription**: Convert audio files to text using advanced transcription services.
- **Smart Summarization**: Generate comprehensive summaries that include overviews, core concepts, detailed explanations, examples, key takeaways, and revision questions.
- **PDF Export**: Easily export your summaries into professional, styled PDF documents.
- **User-Friendly Interface**: Seamlessly navigate through Home, Video, Transcript, and Summary tabs to manage your content.
<p align="center">
<img width="1280" alt="image" src="https://github.com/user-attachments/assets/fce23e0d-14f2-4f82-8cb7-f0eb3f63a984" />

</p>


## Repository Information
This repository is actively maintained on GitHub:

- **Repository**: [its-dhanya/suma](https://github.com/its-dhanya/suma)
- **Stars, Forks, and Issues**: Visit the GitHub repository page for the latest statistics.
- **Latest Commit**: Check the commit history for recent updates and improvements.

## Prerequisites
- [Node.js](https://nodejs.org/) (LTS version recommended)
- [npm](https://www.npmjs.com/) (or [yarn](https://yarnpkg.com/))
- [Python](https://www.python.org/) (if using a Python back-end for transcription/summarization tasks)
- Git
  
## Installation

### Front-End Setup
1. **Clone the Repository**  
   Open your terminal and clone the repository:
   ```bash
   git clone https://github.com/its-dhanya/suma.git
   cd suma
   ```

2. **Install Node Dependencies**  
   Install the required npm packages:
   ```bash
   npm install
   ```
   or if you prefer yarn:
   ```bash
   yarn
   ```

3. **Setup Tauri**  
   Ensure you have Rust and Cargo installed. Then initialize or verify the Tauri configuration:
   - To install Tauri CLI (if not already installed):
     ```bash
     cargo install tauri-cli
     ```
   - To create or update Tauri configuration (this is usually done automatically when building for Tauri):
     ```bash
     npx tauri init
     ```
   Review and update the Tauri configuration files in the `src-tauri` directory if needed.

### Back-End Setup
1. **Navigate to the Back-End Directory**  
   If the FastAPI code is located in a separate directory (e.g., `backend`):
   ```bash
   cd backend
   ```

2. **Create a Virtual Environment** (optional, but recommended)  
   ```bash
   python -m venv venv
   source venv/bin/activate  # For Unix/Mac
   # or for Windows:
   # venv\Scripts\activate
   ```

3. **Install Python Dependencies**  
   Install the required packages using pip:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configuration**  
   Create a `.env` file (if applicable) by copying from the example file:
   ```bash
   cp .env.example .env
   ```
   Then update the `.env` file with your necessary configuration (e.g., API keys, port settings).

## Running the Application

### Starting the Front-End
There are two ways to run the front-end: in development mode, or as a bundled Tauri app.

#### Development
1. Start the React development server:
   ```bash
   npm start
   ```
   or:
   ```bash
   yarn start
   ```
2. Visit the app in your browser at [http://localhost:3000](http://localhost:3000).

#### Tauri (Desktop App)
1. In the project root directory, run:
   ```bash
   npx tauri dev
   ```
   This command builds and runs the Tauri desktop application, combining the React front-end with a native desktop shell.

### Starting the Back-End
1. **Run the FastAPI Server** (from the backend directory):
   ```bash
   uvicorn main:app --reload --port 5001
   ```
   The `--reload` flag enables auto-reloading for code changes.  
2. The FastAPI server will be available at [http://localhost:5001](http://localhost:5001).

## Troubleshooting
- **Node/Tauri Issues:**  
  - Ensure Node.js and npm are up to date.  
  - Verify that Rust and Cargo are properly installed for Tauri.
- **FastAPI Issues:**  
  - Confirm your Python virtual environment is activated.  
  - Double-check that all required dependencies are installed.
- **API Connectivity:**  
  - Ensure that the FastAPI server is running before starting the React or Tauri application.
- **Environment Variables:**  
  - Ensure that the `.env` file has been created and updated with all necessary configurations.
