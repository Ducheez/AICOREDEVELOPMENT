import os
import sys
import json
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
from logging.handlers import RotatingFileHandler
import logging
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)
app.secret_key = os.getenv('SECRET_KEY', os.urandom(24))

# Initialize OpenAI client
openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))


class LegalCategoryManager:
    """Comprehensive Legal Category Management System"""
    
    CATEGORIES = {
        "Family Law": [
            "Adoptions", "Child Custody & Visitation", "Child Support", 
            "Divorce", "Guardianship", "Paternity", "Separations", 
            "Spousal Support or Alimony"
        ],
        "Employment Law": [
            "Disabilities", "Employment Contracts", "Employment Discrimination", 
            "Pensions and Benefits", "Sexual Harassment", "Wages and Overtime Pay", 
            "Workplace Disputes", "Wrongful Termination"
        ],
        "Criminal Law": [
            "General Criminal Defense", "Environmental Violations", "Drug Crimes", 
            "Drunk Driving/DUI/DWI", "Felonies", "Misdemeanors", 
            "Speeding and Moving Violations", "White Collar Crime", "Tax Evasion"
        ],
        "Real Estate Law": [
            "Commercial Real Estate", "Condominiums and Cooperatives", 
            "Construction Disputes", "Foreclosures", "Mortgages", 
            "Purchase and Sale of Residence", "Title and Boundary Disputes"
        ],
        "Business/Corporate Law": [
            "Breach of Contract", "Corporate Tax", "Business Disputes", 
            "Buying and Selling a Business", "Contract Drafting and Review", 
            "Corporations, LLCs, Partnerships, etc.", "Entertainment Law"
        ],
        "Immigration Law": [
            "Citizenship", "Deportation", 
            "Permanent Visas or Green Cards", "Temporary Visas"
        ],
        "Personal Injury Law": [
            "Automobile Accidents", "Dangerous Property or Buildings", 
            "Defective Products", "Medical Malpractice", "Personal Injury (General)"
        ],
        "Wills, Trusts, & Estates Law": [
            "Contested Wills or Probate", "Drafting Wills and Trusts", 
            "Estate Administration", "Estate Planning"
        ],
        "Bankruptcy, Finances, & Tax Law": [
            "Collections", "Consumer Bankruptcy", "Consumer Credit", 
            "Income Tax", "Property Tax"
        ],
        "Government & Administrative Law": [
            "Education and Schools", "Social Security – Disability", 
            "Social Security – Retirement", "Social Security – Dependent Benefits", 
            "Social Security – Survivor Benefits", "Veterans Benefits", 
            "General Administrative Law", "Environmental Law", 
            "Liquor Licenses", "Constitutional Law"
        ],
        "Product & Services Liability Law": [
            "Attorney Malpractice", "Defective Products", 
            "Warranties", "Consumer Protection and Fraud"
        ],
        "Intellectual Property Law": [
            "Copyright", "Patents", "Trademarks"
        ],
        "Landlord/Tenant Law": [
            "Leases", "Evictions", "Property Repairs"
        ]
    }

    FORM_FIELDS = {
        "Family Law": {
            "Adoptions": [
                "age", "maritalStatus", "occupation", "relationshipToChild",
                "custodyStatus", "childrenAges", "motherPosition", "fatherPosition",
                "income", "hiringTimeline"
            ],
            "Child Custody & Visitation": [
                "age", "occupation", "childrenAges", "relationshipStatus",
                "custodyArrangement", "visitationSchedule", "otherParentOccupation",
                "childSupport", "relationship", "income", "otherParentIncome",
                "childCount", "courtOrders", "schoolDistrict", "healthIssues"
            ],
            "Child Support": [
                "age", "occupation", "childrenAges", "relationshipStatus",
                "currentArrangement", "paymentHistory", "otherParentInfo",
                "incomeHistory", "expenses", "healthInsurance", "daycare",
                "education"
            ],
            "Divorce": [
                "age", "occupation", "spouseOccupation", "currentStatus",
                "marriageDate", "separationDate", "childrenCount", "childrenAges",
                "assetHome", "assetVehicles", "assetInvestment", "assetStocks",
                "assetCash", "debtCredit", "debtMortgage", "debtVehicle",
                "debtPersonal", "debtMedical", "mediationStatus", "income",
                "spouseIncome", "pensionInfo", "businessInterests", "inheritances"
            ],
            "Guardianship": [
                "age", "maritalStatus", "occupation", "guardianshipType",
                "wardInfo", "wardAge", "wardCondition", "currentCaregivers",
                "familyRelations", "medicalNeeds", "financialResources",
                "proposedPlan", "alternativeGuardians"
            ],
            "Paternity": [
                "age", "maritalStatus", "occupation", "childAge",
                "motherInfo", "fatherInfo", "testStatus", "testDate",
                "childSupport", "custodyGoals", "visitation", "birthCertificate"
            ],
            "Separations": [
                "age", "occupation", "spouseInfo", "marriageDate",
                "separationDate", "propertyDivision", "debtDivision",
                "livingArrangements", "supportRequests", "childrenPlans",
                "reconciliationStatus", "counselingStatus"
            ],
            "Spousal Support": [
                "age", "occupation", "spouseOccupation", "marriageLength",
                "separationStatus", "incomeHistory", "expenses", "healthStatus",
                "educationLevel", "employmentCapacity", "standardOfLiving",
                "retirementInfo"
            ]
        },
        "Employment Law": {
            "Disabilities": [
                "hireDate", "jobTitle", "employmentStatus", "employerRelationship",
                "organizationType", "industry", "employeeCount", "disability",
                "accommodationRequested", "accommodationStatus", "medicalDocumentation",
                "workLimitations", "employerResponse", "retaliation", "income",
                "benefits", "unionStatus"
            ],
            "Employment Contracts": [
                "hireDate", "jobTitle", "employmentStatus", "contractType",
                "duration", "compensation", "benefits", "duties",
                "nonCompete", "termination", "intellectualProperty",
                "confidentiality", "disputeResolution"
            ],
            "Employment Discrimination": [
                "hireDate", "jobTitle", "discriminationType", "incidentDates",
                "perpetrators", "witnesses", "evidence", "reporting",
                "employerResponse", "damages", "remedies", "eeocStatus"
            ],
            "Pensions and Benefits": [
                "employmentDuration", "pensionType", "benefitsClaimed",
                "denialReason", "appealStatus", "healthInsurance",
                "disability", "retirement", "vestingStatus", "beneficiaries"
            ],
            "Sexual Harassment": [
                "employmentInfo", "harassmentType", "incidentDates",
                "perpetrator", "witnesses", "evidence", "reportingHistory",
                "employerResponse", "retaliation", "damages", "remediesSought"
            ],
            "Wages and Overtime": [
                "employmentDates", "payRate", "overtimeRate", "hoursWorked",
                "unpaidWages", "mealBreaks", "paymentHistory", "classification",
                "deductions", "commissions", "bonuses"
            ],
            "Workplace Disputes": [
                "employmentInfo", "disputeNature", "partiesInvolved",
                "incidentDates", "witnesses", "evidence", "resolution",
                "damages", "remediesSought", "workplacePolicy"
            ],
            "Wrongful Termination": [
                "employmentDates", "terminationDate", "terminationReason",
                "priorPerformance", "warnings", "documentation", "witnesses",
                "damages", "mitigationEfforts", "unemployment"
            ]
        },
        "Criminal Law": {
            "General Criminal Defense": [
                "arrestDate", "charges", "jurisdiction", "bailStatus",
                "priorRecord", "evidenceList", "witnesses", "policeBehavior",
                "statementsMade", "alibi"
            ],
            "Environmental Violations": [
                "violationType", "location", "dateDiscovered", "regulationsViolated",
                "damages", "cleanup", "permits", "inspections", "priorViolations",
                "complianceEfforts"
            ],
            "Drug Crimes": [
                "arrestDate", "substanceType", "quantity", "charges",
                "searchDetails", "seizure", "testing", "priorDrugOffenses",
                "treatmentHistory", "codefendants"
            ],
            "DUI/DWI": [
                "arrestDate", "location", "stopReason", "sobrietyTests",
                "breathalyzer", "bloodTest", "policeConduct", "priorDUI",
                "license", "vehicle"
            ],
            "Felonies": [
                "charges", "arrestInfo", "evidence", "witnesses",
                "alibi", "codefendants", "dealOffered", "priorFelonies",
                "sentencingRisks", "restitution"
            ],
            "Misdemeanors": [
                "charges", "arrestInfo", "courtDate", "evidence",
                "witnesses", "priorOffenses", "pleaOptions", "penaltyRisks",
                "probation", "fines"
            ],
            "Traffic Violations": [
                "citationDate", "violation", "location", "speed",
                "conditions", "officerInfo", "priorTickets", "license",
                "insurance", "registration"
            ],
            "White Collar Crime": [
                "charges", "scheme", "amount", "victims",
                "timeframe", "evidence", "codefendants", "financialRecords",
                "restitution", "assets"
            ],
            "Tax Evasion": [
                "taxYears", "amountOwed", "filingStatus", "unreportedIncome",
                "deductions", "offshore", "businessInvolvement", "priorAudits",
                "irsContact", "accountant"
            ]
        },
        "Real Estate Law": {
            "Commercial Real Estate": [
                "propertyType", "location", "zoning", "purchasePrice",
                "financing", "tenants", "leases", "improvements",
                "environmentalIssues", "permits", "restrictions", "insurance"
            ],
            "Condominiums and Cooperatives": [
                "propertyInfo", "purchasePrice", "monthlyCharges", "bylaws",
                "boardApproval", "restrictions", "amenities", "repairs",
                "insurance", "assessments", "reserves"
            ],
            "Construction Disputes": [
                "projectType", "contractValue", "timeline", "defects",
                "delays", "changeOrders", "payments", "materials",
                "subcontractors", "permits", "inspections", "damages"
            ],
            "Foreclosures": [
                "propertyInfo", "loanDetails", "defaultDate", "missedPayments",
                "totalOwed", "marketValue", "equity", "lenderContact",
                "modificationEfforts", "bankruptcyStatus", "redemptionRights",
                "deficiencyJudgment"
            ],
            "Mortgages": [
                "propertyInfo", "loanType", "loanAmount", "interestRate",
                "term", "monthlyPayment", "downPayment", "escrow",
                "insurance", "taxes", "pmi", "prepaymentPenalty",
                "closingCosts"
            ],
            "Purchase and Sale": [
                "propertyType", "location", "purchasePrice", "closingDate",
                "contingencies", "financing", "inspection", "appraisal",
                "earnestMoney", "repairs", "disclosures", "titleInsurance",
                "survey", "possession", "prorations"
            ],
            "Title and Boundary": [
                "propertyInfo", "disputeType", "surveyInfo", "titleHistory",
                "encroachments", "easements", "deedRestrictions", "neighbors",
                "improvements", "landUse", "zoning", "permits", "damages",
                "remedies"
            ]
        },
        "Business/Corporate Law": {
            "Breach of Contract": [
                "contractType", "contractDate", "parties", "terms",
                "breach", "damages", "performance", "notices",
                "remedies", "negotiations", "mitigation", "deadlines"
            ],
            "Corporate Tax": [
                "entityType", "taxYears", "revenue", "expenses",
                "deductions", "credits", "foreignIncome", "stateObligations",
                "audits", "penalties", "compliance", "planning"
            ],
            "Buying and Selling a Business": [
                "businessType", "salePrice", "assets", "liabilities",
                "agreements", "taxes", "due diligence", "transitional services",
                "non-compete", "indemnification", "closing"
            ],
            "Contract Drafting and Review": [
                "contractType", "parties", "duration", "termination",
                "compensation", "intellectual property", "confidentiality",
                "dispute resolution", "representations and warranties",
                "conditions precedent", "indemnification"
            ],
            "Corporations, LLCs, Partnerships, etc.": [
                "entityType", "owners", "management", "governance",
                "capital structure", "taxes", "compliance", "dissolution",
                "mergers and acquisitions", "financing"
            ],
            "Entertainment Law": [
                "client", "industry", "agreements", "intellectual property",
                "licensing", "royalties", "distribution", "financing",
                "compliance", "disputes"
            ]
        },
        "Intellectual Property Law": {
            "Copyright": [
                "workType", "creationDate", "registration", "author",
                "ownership", "infringement", "damages", "licensing",
                "assignments", "notices", "international", "fairUse"
            ],
            "Patents": [
                "inventionType", "filingDate", "publicationDate", "inventors",
                "assignees", "claims", "priorArt", "infringement",
                "licensing", "maintenance", "international", "prosecution"
            ],
            "Trademarks": [
                "mark", "goods", "services", "filingDate",
                "useDate", "registration", "classes", "distinctiveness",
                "opposition", "infringement", "licensing", "renewal",
                "international"
            ]
        },
        "Landlord/Tenant Law": {
            "Leases": [
                "propertyType", "term", "rent", "deposit",
                "utilities", "maintenance", "occupants", "pets",
                "parking", "modifications", "subletting", "insurance",
                "termination"
            ],
            "Evictions": [
                "propertyInfo", "tenantInfo", "reason", "notices",
                "rentOwed", "damages", "violations", "evidence",
                "courtDates", "possession", "personalProperty", "judgment"
            ],
            "Repairs and Maintenance": [
                "propertyInfo", "issue", "reportDate", "severity",
                "notices", "repairs", "costs", "contractor",
                "permits", "inspections", "violations", "reimbursement",
                "warranty"
            ]
        },
        "Government & Administrative Law": {
            "Education and Schools": [
                "studentInfo", "schoolInfo", "disciplineIssue",
                "specialNeeds", "discrimination", "admissions",
                "504Plan", "IEP", "harassment", "bullying"
            ],
            "Social Security – Disability": [
                "medicalCondition", "disabilityDetails", "workHistory",
                "applicationDate", "decisionDate", "appeals",
                "supplementalIncome", "Medicare", "Medicaid"
            ],
            "Social Security – Retirement": [
                "retirementDate", "earningsHistory", "otherBenefits",
                "spouseInfo", "dependentInfo", "taxes", "appeals"
            ],
            "Social Security – Dependent Benefits": [
                "parentInfo", "childInfo", "deceasedWorkerInfo",
                "applicationDate", "eligibility", "appeals", "taxes"
            ],
            "Social Security – Survivor Benefits": [
                "deceasedWorkerInfo", "survivorInfo", "childInfo",
                "applicationDate", "eligibility", "appeals", "taxes"
            ],
            "Veterans Benefits": [
                "serviceRecord", "disabilityDetails", "claimedBenefits",
                "applicationDate", "appeals", "VA Healthcare",
                "education", "housing"
            ],
            "Environmental Law": [
                "violationType", "location", "dateDiscovered", "regulationsViolated",
                "damages", "cleanup", "permits", "inspections", "priorViolations",
                "complianceEfforts"
            ],
            "Liquor Licenses": [
                "businessInfo", "licenseType", "applicationDate",
                "zoning", "previousViolations", "protests", "hearings",
                "renewals", "suspensions"
            ],
            "Constitutional Law": [
                "rightViolated", "government_entity", "legal_theory",
                "standing", "damages", "injunctive_relief", "appeals"
            ]
        },
        "Product & Services Liability Law": {
            "Attorney Malpractice": [
                "attorneyInfo", "caseDetails", "errorType",
                "damages", "expertsRetained", "standardOfCare",
                "claimHistory", "insuranceInfo"
            ],
            "Defective Products": [
                "productInfo", "defectDescription", "injuryDetails",
                "userInfo", "userConduct", "recalls", "regulations",
                "expertsRetained", "damages"
            ],
            "Warranties": [
                "productInfo", "warrantyType", "warrantyTerms",
                "failureDescription", "repairAttempts", "damageCaused",
                "economicLoss", "revocationOfAcceptance"
            ],
            "Consumer Protection and Fraud": [
                "fraudType", "victimInfo", "schemeDescription",
                "monetaryLoss", "victimVulnerability", "deceptionMethods",
                "governmentInvolvement", "consumerProtectionStatutes"
            ]
        }
    }

    @classmethod
    def validate_category(cls, category: str, subcategory: str) -> bool:
        """Validate if category and subcategory exist"""
        category = category.strip().replace('EXACTLY', '').strip("'")
        subcategory = subcategory.strip().replace('EXACTLY', '').strip("'")
        return (category in cls.CATEGORIES and 
                subcategory in cls.CATEGORIES[category])
    @classmethod
    def get_form_fields(cls, category: str, subcategory: str) -> list:
        """Get the form fields for the specified category and subcategory"""
        category = category.strip().replace('EXACTLY', '').strip("'")
        subcategory = subcategory.strip().replace('EXACTLY', '').strip("'")
        
        if category not in cls.FORM_FIELDS:
            logger.error(f"Category not found: {category}")
            return []
            
        if subcategory not in cls.FORM_FIELDS[category]:
            logger.error(f"Subcategory not found: {subcategory}")
            return []
            
        return cls.FORM_FIELDS[category].get(subcategory, [])
        
class PIIRemover:
    """Advanced Personally Identifiable Information Removal Utility"""
    
    @staticmethod
    def clean_text(text: str) -> str:
        """Comprehensive PII removal method"""
        import re
        patterns = [
            (r'\b\d{1,2}/\d{1,2}/\d{4}\b', '[DATE]'),
            (r'\b[A-Z][a-z]+ [A-Z][a-z]+\b', '[NAME]'),
            (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]'),
            (r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]'),
            (r'\b\d+\s+[A-Z][a-z]+\s+(Street|Ave|Road|Boulevard)\b', '[LOCATION]')
        ]
        
        for pattern, replacement in patterns:
            text = re.sub(pattern, replacement, text)
        
        return text

class LegalPromptGenerator:
    """Dynamic Legal Prompt Generation System"""
    
    
    
    @classmethod
    def generate_prompt(cls, category: str, subcategory: str) -> str:
       
       return f"""You are a professional legal summarizer assisting a {category} attorney 
    specializing in {subcategory} cases in reviewing potential client leads.
    Requirements:
    1. STRICTLY FORBIDDEN: Do not include or reference the original case description
    2. STRICTLY FORBIDDEN: Remove ALL Personally Identifiable Information (PII):
       - Names of any individuals (replace with roles like "prospective adoptive parents", "minor child")
       - Dates (including birthdates, filing dates, incident dates)
       - Email addresses (any email format)
       - Phone numbers (any format)
       - Physical locations (addresses, cities, states)
    3. Each bullet point should be a complete, professional statement
    4. Use formal legal terminology appropriate for {category} cases
    5. Focus only on legal aspects, requirements, and considerations
    6. Each section must be in bullet point format using <ul> and <li> tags
    7. Keep descriptions abstract and applicable to similar cases
    8. Use only generic terms and roles instead of specific identifiers

    Output Format (JSON):
    {{
      "summary": "HTML formatted summary with sections:
                  <h3>General Case Summary</h3>
                  <ul>
                    [3-4 bullet points summarizing core legal situation]
                  </ul>
                  <h3>Key aspects of the case</h3>
                  <ul>
                    [4-5 bullet points listing key legal components]
                  </ul>
                  <h3>Potential Merits of case and Legal Considerations</h3>
                  <ul>
                    [4-5 bullet points analyzing legal merits and strategies]
                  </ul>",

      "mainCategory": "EXACTLY '{category}'",
      "subCategory": "EXACTLY '{subcategory}'",
      "confidence": "high/medium/low"
    }}

    Requirements:
    1. STRICTLY FORBIDDEN: Do not include or reference the original case description
    2. STRICTLY FORBIDDEN: Remove ALL Personally Identifiable Information (PII):
       - Names of any individuals (replace with roles like "prospective adoptive parents", "minor child")
       - Dates (including birthdates, filing dates, incident dates)
       - Email addresses (any email format)
       - Phone numbers (any format)
       - Physical locations (addresses, cities, states)
    3. Each bullet point should be a complete, professional statement
    4. Use formal legal terminology appropriate for {category} cases
    5. Focus only on legal aspects, requirements, and considerations
    6. Each section must be in bullet point format using <ul> and <li> tags
    7. Keep descriptions abstract and applicable to similar cases
    8. Use only generic terms and roles instead of specific identifiers"""
class CaseTitleGenerator:
    """Generates professional, anonymized case titles"""
    
    @staticmethod
    def generate_title(category: str, subcategory: str) -> str:
        """Generate a professional case title"""
        return f"{category} - {subcategory} Legal Matter"

class CategoryPredictor:
    """Advanced Legal Category Prediction System"""

    @retry(
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(Exception),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def predict_category(self, case_summary: str) -> dict:
        """Predict legal category and generate comprehensive summary"""
        try:
            if not openai_client.api_key:
                raise ValueError("OPENAI_API_KEY is not set in environment variables")

            # Clean summary
            clean_summary = PIIRemover.clean_text(case_summary)
            
            # Predict category using OpenAI
            response = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system", 
                        "content": f"""You are an expert legal category classifier. 
                        Analyze the case summary and return the most appropriate 
                        legal category from: {json.dumps(LegalCategoryManager.CATEGORIES)}
                        Your response must be a valid JSON object with 'mainCategory' and 'subCategory' fields."""
                    },
                    {"role": "user", "content": f"Classify the following case summary: {clean_summary}"}
                ],
                response_format={"type": "json_object"}
            )
            
            # Parse category prediction
            prediction = json.loads(response.choices[0].message.content)
            
            # Validate category
            if not LegalCategoryManager.validate_category(
                prediction.get('mainCategory', ''), 
                prediction.get('subCategory', '')
            ):
                return {
                    "summary": "<h3>Invalid Category</h3><p>Unable to classify the case.</p>",
                    "mainCategory": "Unknown",
                    "subCategory": "General Consultation",
                    "confidence": "low"
                }
            
            # Generate prompt
            prompt = LegalPromptGenerator.generate_prompt(
                prediction['mainCategory'], 
                prediction['subCategory']
            )
            
            # Generate summary
            summary_response = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                    "role": "system",
                    "content": prompt + " Ensure to create a completely new summary without including the original text."
                },
                {
                    "role": "user",
                    "content": f"Based on this case information, generate a professional legal summary: {clean_summary}"
                }
            ],
            response_format={"type": "json_object"}
        )
            
            # Parse summary
            final_summary = json.loads(summary_response.choices[0].message.content)
            
            # Generate case title
            case_title = CaseTitleGenerator.generate_title(
                prediction['mainCategory'], 
                prediction['subCategory']
            )
            
            # Add case title to summary
            final_summary['caseTitle'] = case_title
            
            return final_summary
        
        except Exception as e:
            logger.error(f"Category prediction error: {e}")
            return {
                "summary": f"<h3>Error</h3><p>Unable to process summary: {str(e)}</p>",
                "mainCategory": "Unknown",
                "subCategory": "General Consultation",
                "confidence": "low",
                "caseTitle": "Unclassified Legal Matter"
            }

def generate_form_html(category, subcategory, form_fields):
    """
    Generate dynamic form HTML based on category, subcategory, and form fields
    """
    form_id = f"{category.lower().replace(' ', '-')}-{subcategory.lower().replace(' ', '-')}-form"
    
    html = f"""
    <div class="form-container">
        <h2 class="form-title">{category} - {subcategory} Case Information</h2>
        <form id="{form_id}">
            <input type="hidden" name="category" value="{category}">
            <input type="hidden" name="subcategory" value="{subcategory}">
    """
    
    for field in form_fields:
        html += f"""
            <div class="form-group">
                <label for="{field}" class="form-label">{field.replace('_', ' ').title()}</label>
                <input type="text" id="{field}" name="{field}" class="form-control" />
            </div>
        """
    
    html += """
            <div class="form-navigation">
                <button type="button" class="nav-button back-button" onclick="window.categoryPredictor.resetForm()">
                    Back to Summary
                </button>
                <button type="submit" class="nav-button submit-button">
                    Submit Case Details
                </button>
            </div>
        </form>
    </div>
    """
    
    return html

# Flask Routes
@app.route('/')
def index():
    """Render main application page"""
    return render_template('index.html')

@app.route('/predict-category', methods=['POST'])
def predict_category():
    """Handle category prediction request"""
    try:
        data = request.get_json()
        summary = data.get('summary', '')
        
        if not summary:
            return jsonify({"error": "No summary provided"}), 400
        
        predictor = CategoryPredictor()
        result = predictor.predict_category(summary)
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Category prediction endpoint error: {e}")
        return jsonify({
            "error": "Internal server error",
            "mainCategory": "Unknown",
            "subCategory": "General Consultation",
            "confidence": "low"
        }), 500

@app.route('/get-form-template', methods=['POST'])
def get_form_template():
    """
    Generate and return a form template based on selected category and subcategory
    """
    try:
        logger.info("Received form template request:")
        data = request.get_json()
        logger.info(f"Request data: {data}")

        category = data.get('category', '').strip().replace('EXACTLY', '').strip("'")
        subcategory = data.get('subcategory', '').strip().replace('EXACTLY', '').strip("'")
        
        logger.info(f"Processing request for category: {category}, subcategory: {subcategory}")

        if not category or not subcategory:
            logger.warning("Missing category or subcategory")
            return jsonify({
                "error": "Category and subcategory are required",
                "received_data": data
            }), 400

        if not LegalCategoryManager.validate_category(category, subcategory):
            logger.warning(f"Invalid category or subcategory: {category}, {subcategory}")
            return jsonify({
                "error": "Invalid category or subcategory",
                "category": category,
                "subcategory": subcategory
            }), 400
        
        # Fetch the form fields for the selected category and subcategory
        form_fields = LegalCategoryManager.get_form_fields(category, subcategory)
        logger.info(f"Retrieved {len(form_fields)} form fields")

        form_html = generate_form_html(category, subcategory, form_fields)
        
        return jsonify({
            "html": form_html,
            "fields": form_fields
        })

    except Exception as e:
        logger.error(f"Form template error: {str(e)}", exc_info=True)
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500
@app.route('/submit_form', methods=['POST'])
def submit_form():
    """
    Handle form submission with more robust processing
    """
    try:
        form_data = request.form.to_dict()
        print("Received form data:", form_data)

        required_fields = ['case_description', 'main_category', 'sub_category']
        missing_fields = [field for field in required_fields if not form_data.get(field)]

        if missing_fields:
            return jsonify({
                "success": False, 
                "error": f"Missing fields: {', '.join(missing_fields)}"
            }), 400

        return jsonify({
            "success": True, 
            "referenceNumber": "REF-" + str(hash(form_data.get('case_description')))[1:7],
            "message": "Case submitted successfully"
        })
    
    except Exception as e:
        print(f"Form submission error: {e}")
        return jsonify({
            "success": False, 
            "error": "Error processing form submission"
        }), 500

if __name__ == '__main__':
    app.run(debug=True)