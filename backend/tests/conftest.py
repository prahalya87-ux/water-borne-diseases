import os

# Must run before the app is imported anywhere.
os.environ["DATABASE_URL"] = "sqlite:///./test_waterguard.db"
os.environ["UPLOAD_DIR"] = "./test_uploads"
os.environ["AUTO_CREATE_TABLES"] = "true"