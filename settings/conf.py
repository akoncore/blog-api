from decouple import config



#-----------------------------
#ENV_ID
#
ENV_POSSIBLE_OPTIONS = (
    "local",
    "prod"
)
ENV_ID = config("BLOG_ENV_ID",cast=str)
SECRET_KEY = 'django-insecure-+ada5^xvx&doe5tpzsdnlu6qb%llv6*^#4l@rh@tz((5*!u!vw'

