"""
Challenge App F — Complex Forms Application with Multi-Step Wizard & Dependent Inputs.
Defects:
1. Step 2 submit /submit/step2 with age=100 returns HTTP 500 (API Boundary Error)
2. Step 1 allows invalid email "invalid-email-address" without validation (Validation Defect)
3. State dropdown change event causes JS TypeError (JavaScript Error)
"""
from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse

app = FastAPI(title="Challenge Complex Forms App")


@app.get("/", response_class=HTMLResponse)
def wizard_step1():
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Registration Wizard - Step 1</title></head>
    <body>
        <h1>Registration Wizard (Step 1 of 2)</h1>
        <form action="/submit/step1" method="post">
            <label for="full_name">Full Name:</label>
            <input type="text" id="full_name" name="full_name" required /><br/>
            
            <label for="email">Email Address:</label>
            <!-- DEFECT: Missing type="email" and no backend validation check -->
            <input type="text" id="email" name="email" /><br/>
            
            <button type="submit" id="btn-next">Next: Step 2</button>
        </form>
    </body>
    </html>
    """


@app.post("/submit/step1")
def submit_step1(full_name: str = Form(...), email: str = Form("")):
    # Allows any string email without validation!
    return RedirectResponse(url="/wizard/step2", status_code=303)


@app.get("/wizard/step2", response_class=HTMLResponse)
def wizard_step2():
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Registration Wizard - Step 2</title></head>
    <body>
        <h1>Registration Wizard (Step 2 of 2)</h1>
        <form action="/submit/step2" method="post">
            <label for="age">Age (Years):</label>
            <input type="number" id="age" name="age" required /><br/>
            
            <label for="country">Country:</label>
            <select id="country" name="country" onchange="updateStates()">
                <option value="US">United States</option>
                <option value="CA">Canada</option>
            </select><br/>
            
            <label for="state">State / Province:</label>
            <select id="state" name="state">
                <option value="NY">New York</option>
            </select><br/>
            
            <button type="submit" id="btn-finish">Complete Registration</button>
        </form>

        <script>
        function updateStates() {
            // DEFECT: Dependent dropdown bug!
            var data = {};
            console.log(data.states.list);
        }
        </script>
    </body>
    </html>
    """


@app.post("/submit/step2")
def submit_step2(age: int = Form(...), country: str = Form("US"), state: str = Form("NY")):
    # DEFECT: Boundary age value 100 triggers HTTP 500 error!
    if age == 100:
        raise HTTPException(status_code=500, detail="Registration Engine Boundary Exception: Age 100 Overflow")
    return HTMLResponse("<h1>Registration Complete! Welcome aboard.</h1>", status_code=200)
