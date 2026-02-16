"""Therapeutics Landscape Tool for F-Prime MCP Server."""

import boto3
import json
import requests
from functools import lru_cache
from pyairtable import Base, Api


@lru_cache(maxsize=1)
def get_secrets() -> dict:
    """Fetch secrets from AWS Secrets Manager."""
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name='us-east-2'
    )
    response = client.get_secret_value(SecretId='resource_logins')
    return json.loads(response['SecretString'])


BOX_BASE = 'app5UNM2QAx82W51F'
BOX_TABLE = 'tblI1yQG9E29bCxf0'
WEBSITE_BASE = 'apphoxAZN32kVwxUg'
WEBSITE_TABLE = 'tblPaRzrVeKmaLh1A'



def query_box(target: str, indication: str, molecule_type: str) -> list:
    """Query Box/Airtable for therapeutics data."""
    secrets = get_secrets()
    airtable_api = secrets['airtable_api']
    
    target = target.lower().replace('-', '')
    indication = indication.lower()
    molecule_type = molecule_type.lower()
    
    if molecule_type.endswith('y'):
        molecule_type = molecule_type[:-1]
    
    table = Base(Api(airtable_api), BOX_BASE).table(BOX_TABLE)
    
    formula = (
        f'AND('
        f'FIND("{target}",SUBSTITUTE(LOWER({{genes}}),"-",""))>0,'
        f'FIND("{indication}",LOWER({{indications}}))>0,'
        f'OR(FIND("{molecule_type}",LOWER({{summary}}))>0,'
        f'FIND("{molecule_type}",LOWER({{technology}}))>0))'
    )
    
    results = table.all(formula=formula)
    return [f.get('fields') for f in results]


def query_websites(target: str, indication: str, molecule_type: str) -> list:
    """Query websites Airtable for therapeutics data."""
    secrets = get_secrets()
    airtable_api = secrets['airtable_api']
    
    target = target.lower().replace('-', '')
    indication = indication.lower()
    molecule_type = molecule_type.lower()
    
    if molecule_type.endswith('y'):
        molecule_type = molecule_type[:-1]
    
    table = Base(Api(airtable_api), WEBSITE_BASE).table(WEBSITE_TABLE)
    
    formula = (
        f'AND('
        f'FIND("{target}",SUBSTITUTE(LOWER({{pipeline}}),"-",""))>0,'
        f'FIND("{indication}",LOWER({{pipeline}}))>0,'
        f'FIND("{molecule_type}",LOWER({{pipeline}}))>0)'
    )
    
    results = table.all(formula=formula)
    return [f.get('fields') for f in results]


def query_globaldata(target: str, indication: str, molecule_type: str) -> list:
    """Query GlobalData API for therapeutics data."""
    secrets = get_secrets()
    globaldata_token = secrets['globaldata_token']
    
    target = target.lower()
    indication = indication.lower()
    molecule_type = molecule_type.lower()
    
    params = {'TokenId': globaldata_token}
    if target:
        params['Target'] = target
    if indication:
        params['Indication'] = indication
    if molecule_type:
        params['MoleculeType'] = molecule_type
    
    r = requests.get(
        'https://apidata.globaldata.com/GlobalDataPharmaFPrimeCapital/api/Drugs/GetPipelineDrugDetails',
        params=params
    )
    
    if r.status_code == 200:
        results = r.json().get('PipelineDrugs', [])
    else:
        return []
    
    # Group by company
    companies = {}
    for drug in results:
        co_name = drug.get('Company_Name')
        co_id = drug.get('CompanyID')
        if co_id in companies:
            companies[co_id]['Drugs'].append(drug)
        else:
            companies[co_id] = {
                'Drugs': [drug],
                'Company_Name': co_name,
                'CompanyID': co_id
            }
    
    return list(companies.values())


def parse_globaldata_results(globaldata: list) -> list:
    """Parse GlobalData results into flat structure."""
    parsed = []
    
    for company in globaldata:
        drugs = company.get('Drugs', [])
        co_name = company.get('Company_Name')
        
        for drug in drugs:
            pipeline = drug.get('PipelineDetails', [])
            
            for p in pipeline:
                parsed.append({
                    'company_name': co_name,
                    'drug_name': drug.get('Drug_Name'),
                    'alias': drug.get('Alias'),
                    'description': drug.get('Product_Description'),
                    'route_of_administration': drug.get('Route_of_Administration'),
                    'target': drug.get('Target'),
                    'molecule_type': drug.get('Molecule_Type'),
                    'ATC_classification': drug.get('ATC_Classification'),
                    'mechanism_of_action': drug.get('Mechanism_of_Action'),
                    'mono_combination': drug.get('MonoCombinationDrug'),
                    'stage': p.get('Development_Stage'),
                    'indication': p.get('Indication'),
                    'therapy_area': p.get('Therapy_Area'),
                    'geography': p.get('Product_Geography'),
                    'line_of_therapy': p.get('Line_of_Therapy'),
                    'last_development_stage': p.get('Last_Development_Stage'),
                    'reason_for_discontinuation': p.get('Reason_for_Discontinuation'),
                    'date_of_discontinuation': p.get('Inactive_Discontinued_Date'),
                })
    
    return parsed


def query_therapeutics_landscape(
    target: str = '',
    indication: str = '',
    molecule_type: str = '',
    sources: list[str] | None = None,
) -> dict:
    """
    Query the therapeutics landscape across multiple data sources.
    
    Args:
        target: Target gene/protein (e.g., "EGFR", "HER2")
        indication: Disease indication (e.g., "lung cancer", "breast cancer")
        molecule_type: Type of molecule (e.g., "antibody", "small molecule")
        sources: List of sources to query: ["box", "websites", "globaldata"]
                 If None, queries all sources.
    
    Returns:
        Dictionary with results from each source.
    """
    if not target and not indication and not molecule_type:
        return {'error': 'At least one of target, indication, or molecule_type is required'}
    
    if sources is None:
        sources = ['box', 'websites', 'globaldata']
    
    results = {
        'query': {
            'target': target,
            'indication': indication,
            'molecule_type': molecule_type,
            'sources': sources,
        },
        'box_results': None,
        'website_results': None,
        'globaldata_results': None,
    }
    
    if 'box' in sources:
        try:
            results['box_results'] = query_box(target, indication, molecule_type)
        except Exception as e:
            results['box_results'] = {'error': str(e)}
    
    if 'websites' in sources:
        try:
            results['website_results'] = query_websites(target, indication, molecule_type)
        except Exception as e:
            results['website_results'] = {'error': str(e)}
    
    if 'globaldata' in sources:
        try:
            raw_results = query_globaldata(target, indication, molecule_type)
            results['globaldata_results'] = parse_globaldata_results(raw_results)
        except Exception as e:
            results['globaldata_results'] = {'error': str(e)}
    
    return results