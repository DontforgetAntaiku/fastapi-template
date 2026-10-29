from app.database.models import User

UserOut = User.get_pydantic_model()
UserIn = User.get_input_model()
UserUpdate = User.get_update_model()
