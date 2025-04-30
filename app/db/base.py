from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
import app.models.student
import app.models.video
import app.models.lecture
import app.models.drowsiness_level
import app.models.watch_history
import app.models.enrollment
import app.models.instructor
import app.models.token
import app.models.instructor_refresh_token
import app.models.admin_refresh_token