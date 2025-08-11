# Documentation de l'API Score

Cette documentation décrit les différentes routes disponibles dans l'API Score, leurs méthodes, les données attendues et les réponses associées.

---

## 1. Ajouter un pays

**Méthode :** `POST`  
**URL :** `http://127.0.0.1:8000/score/add-country/`  

**Headers :**
- `Authorization` : Bearer `<token>`

**Body :**
```json
{
  "name": "Pakistan",
  "email": "just_pakistan@pakistan.org",
  "country_code": "PAK",
  "phone_code": "+92"
}
```

## 2. Nouvelle souscription

**Méthode :** `POST`  
**URL :** `http://127.0.0.1:8000/score/subscribe/`  

**Headers :**
- `Authorization` : Bearer `<token>`

**Body :**
```json
{
  "name": "Pakistan",
  "plan": "monthly"
}
```

## 3. Connexion

**Méthode :** `POST`  
**URL :** `http://127.0.0.1:8000/score/login/`  

**Body :**
```json
{
  "email": "islamabad@office.com",
  "password": "dUpyimg20ZsgYnfDD5-X"
}
```

## 4. Changer le mot de passe

**Méthode :** `POST`  
**URL :** `http://127.0.0.1:8000/score/change-password/`  

**Headers :**
- `Authorization` : Bearer `<token>`

**Body :**
```json
{
  "old_password": "dUpyimg20ZsgYnfDD5-X",
  "new_password": "Islamabad2025"
}
```

## 5. Informations sur le bureau

**Méthode :** `POST`  
**URL :** `http://127.0.0.1:8000/score/office-info/`  

**Headers :**
- `Authorization` : Bearer `<token>`

**Body :**
```json
{
  "front_office_name": "Islamabad",
  "username": "Islamabad",
  "npi": "90283993234",
  "phone": "559023399",
  "email": "islamabad@office.com",
  "localisation": "Islamabad Est rue sergent"
}
```

