# Docker_template
Docker template for python_Django_Mysql
`# docker-django

This is intended to be used as a template repository for django projects running with docker and docker-compose

- [docker-django](#docker-django)
  - [Building & commands](#building--commands)
      - [Your first step is start building your project with the following line](#your-first-step-is-start-building-your-project-with-the-following-line)
      - [Database settings change to your select DB](#database-settings-change-to-your-select-db)
      - [then create your own pages with](#then-create-your-own-pages-with)
      - [Alwys remember to run the migrate command](#alwys-remember-to-run-the-migrate-command)
      - [If you want to create a new super user](#if-you-want-to-create-a-new-super-user)
      - [and finally just docker-compose up](#and-finally-just-docker-compose-up)

---

## Building & commands

#### Your first step is start building your project with the following line
`
`docker-compose run web django-admin startproject djangoexample .`

#### Database settings change to your select DB
Go to your settings.py inside the project folder created in previous steps and modify it accordingly your database settings. Here an example:

```
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'Database_Name', #as Initial.sql
        'USER': 'user',
        'PASSWORD': 'pass',
        'HOST': 'db',
        'PORT': 3306,
    }
}
```

#### then create your own pages with 

 `docker-compose run web python manage.py startapp polls`

#### Always remember to run the migrate command

`docker-compose run web python manage.py migrate`


#### If you want to create a new super user

`docker-compose run web python manage.py createsuperuser`


#### and finally just docker-compose up

`docker-compose up`

### If doesn't work try with
"""first step 
docker-compose up db
second step:
docker-compose up web"""