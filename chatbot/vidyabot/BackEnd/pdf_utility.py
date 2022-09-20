import pdfkit
import firebase_admin
from firebase_admin import credentials, storage, firestore
from flask import Flask, make_response, request
from flask_cors import CORS


app = Flask(__name__)
CORS(app)
app.config["JSON_AS_ASCII"] = False


subjects = [
    "stem",
    "vocational courses",
    "defense",
    "commerce & management",
    "jobs as soon as possible",
    "civil services",
    "creative & argumentative studies",
]
tests = ["aptitude_test", "interest_test", "personality_marks", "interest_test"]


class Test_data:
    def __init__(self):
        self.data = {}
        for test in tests:
            self.data[test] = {}
            for subject in subjects:
                self.data[test][subject] = "not given"


def init_bucket():
    cred = credentials.Certificate("NK_key.json")
    firebase_admin.initialize_app(
        cred,
        {
            "storageBucket": "nakshekadam2022.appspot.com",
            "projectId": "nakshekadam2022",
        },
    )  # connecting to firebase
    bucket = storage.bucket()  # getting the bucket
    db = firestore.client()
    return db, bucket


def upload_to_firebase(bucket, uid):
    blob = bucket.blob(f"reports/{uid}.pdf")  # creating a blob
    blob.upload_from_filename(f"{uid}.pdf")  # uploading the file
    # keep it public
    blob.make_public()


def get_data(db, uid):
    document_list = [
        "background_test",
        "personality_marks",
        "aptitude_test",
        "interest_test",
    ]
    subjects = [
        "stem",
        "vocational courses",
        "defense",
        "commerce & management",
        "jobs as soon as possible",
        "civil services",
        "creative & argumentative studies",
    ]
    self_info = db.collection("users").document(f"{uid}").get().to_dict()
    test_data = Test_data()
    test_data.name = self_info["firstName"] + " " + self_info["lastName"]
    userinfo = (
        db.collection("users")
        .document(uid)
        .collection("data")
        .document("userInfo")
        .get()
        .to_dict()
    )
    test_data.grade = userinfo["class/grade"]
    for document in document_list:
        fb_doc = (
            db.collection("users").document(uid).collection("data").document(document)
        )
        test_data.data[document] = fb_doc.get().to_dict()
    for test in test_data.data:
        if test_data.data[test] is None:
            test_data.data[test] = {}
            for subject in subjects:
                test_data.data[test][subject] = "not given"
        else:
            for subject in subjects:
                # multiply by 100 to get percentage
                if subject in test_data.data[test]:
                    test_data.data[test][subject] = test_data.data[test][subject] * 100
    name = test_data.name
    grade = test_data.grade
    flat_data = flatten_data(test_data.data)
    return name, grade, flat_data


def flatten_data(data):
    flat_data = {}
    for test in data:
        for subject in data[test]:
            flat_data[test + "." + subject] = data[test][subject]
    return flat_data


def generate_html(name, grade, flat_data):
    with open("template.html", "r") as f:
        template = f.read()
        template = template.replace("{{student.name}}", name)
        template = template.replace("{{student.grade}}", grade)
        # replace the placeholders with the data
        for key in flat_data:
            template = template.replace("{{" + key + "}}", str(flat_data[key]))
        # write the html file
    with open("output.html", "w") as f:
        f.write(template)


def generate_pdf(uid):
    pdfkit.from_file("output.html", f"{uid}.pdf")


@app.route("/generate_pdf", methods=["GET", "POST"])
def generate_pdf_route():
    uid = request.args.get("uid")
    name, grade, flat_data = get_data(db, uid)
    generate_html(name, grade, flat_data)
    generate_pdf(uid)
    upload_to_firebase(bucket, uid)
    return "done"


if __name__ == "__main__":
    db, bucket = init_bucket()
    app.run(debug=True, host="0.0.0.0", port=6969)
