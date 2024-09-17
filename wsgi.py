from Project.app import app

if __name__ == "__main__":
    app.logger.info(f"Starting app.py on {app.port}")
    app.run()