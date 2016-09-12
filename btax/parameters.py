"""
Parameters (parameters.py):
-------------------------------------------------------------------------------

This module contains all the parameters used for the calc_final_outputs.py script. It also
contains intermediate calculations that produce more relevant parameters. The parameters
are placed in a dictionary. Last Updated 7/27/2016
"""
from argparse import Namespace
import copy
import json
import os
import pandas as pd
import numpy as np

from btax.util import read_from_egg


DEFAULTS = json.loads(read_from_egg(os.path.join('param_defaults', 'btax_defaults.json')))
DEFAULT_ASSET_COLS = json.loads(read_from_egg(os.path.join('param_defaults', 'btax_results_by_asset.json')))
DEFAULT_INDUSTRY_COLS = json.loads(read_from_egg(os.path.join('param_defaults', 'btax_results_by_industry.json')))


def translate_param_names(**user_mods):
    """Takes parameters names from UI and turns them into names used in btax

    """

    # btax_betr_entity_Switch # If this parameter =True, then u_nc default to corp rate

    defaults = dict(DEFAULTS)
    radio_tags = ('gds', 'ads', 'tax',)
    class_list = [3, 5, 7, 10, 15, 20, 25, 27.5, 39]
    class_list_str = [(str(i) if i != 27.5 else '27_5') for i in class_list]
    user_deprec_system = {}
    for cl in class_list_str:
        if user_mods.get('btax_depr_'+cl+'yr_gds_Switch'):
            user_deprec_system[cl] = 'GDS'
        elif user_mods.get('btax_depr_'+cl+'yr_ads_Switch'):
            user_deprec_system[cl] = 'ADS'
        elif user_mods.get('btax_depr_'+cl+'yr_tax_Switch'):
            user_deprec_system[cl] = 'Economic'
        else:
            user_deprec_system[cl] = 'GDS'
    user_mods.update({k: v['value'][0] for k,v in defaults.iteritems()
                      if k not in user_mods})
    # user_bonus_deprec = {cl: user_mods['btax_depr_{}yr_exp'.format(cl)]/100.
    # 			 for cl in class_list_str}
    # to zero out bonus - useful for compare to CBO
    user_bonus_deprec = {cl: 0.for cl in class_list_str}
    # for expensing
    # user_bonus_deprec = {cl: 1.for cl in class_list_str}


    if user_mods['btax_betr_entity_Switch'] in (True, 'True'):
        u_nc = user_mods['btax_betr_corp']
    else:
        u_nc = user_mods['btax_betr_pass']
    user_params = {
        'u_c': user_mods['btax_betr_corp'],
        'u_nc': u_nc,
        'pi': user_mods['btax_econ_inflat'],
        'i': user_mods['btax_econ_nomint'],
        'ace_c': user_mods['btax_other_corpeq'],
        'int_haircut': user_mods['btax_other_hair'],
        'inv_credit': user_mods['btax_other_invest'],
        'w': user_mods['btax_other_proptx'],
        'bonus_deprec': user_bonus_deprec,
        'deprec_system': user_deprec_system,
    }

    return user_params


def get_params(test_run,baseline,start_year,iit_reform,**user_mods):

    """Contains all the parameters

    	:returns: Inflation rate, depreciation, tax rate, discount rate, return to savers, property tax
    	:rtype: dictionary
    """
    from btax.calc_z import calc_tax_depr_rates, get_econ_depr
    #macro variables
    E_c = 0.058 # CBO (2014) 0.07
    f_c = 0.32 # CBO (2014)0.41
    f_nc = 0.29 # CBO (2014) 0.32
    f_array = np.array([[f_c, f_nc], [1, 1], [0,0]])

    #calibration variables
    omega_scg = 0.03627
    omega_lcg = 0.48187
    omega_xcg = 0.48187

    alpha_c_e_ft = 0.584
    alpha_c_e_td = 0.058
    alpha_c_e_nt = 0.358

    alpha_c_d_ft = 0.460
    alpha_c_d_td = 0.213
    alpha_c_d_nt = 0.327

    alpha_nc_d_ft = 0.691
    alpha_nc_d_td = 0.142
    alpha_nc_d_nt = 0.167

    alpha_h_d_ft = 0.716
    alpha_h_d_td = 0.071
    alpha_h_d_nt = 0.213

    #user defined variables
    user_params = translate_param_names(**user_mods)
    pi = user_params['pi']
    i = user_params['i']
    u_c = user_params['u_c']
    u_nc = 0.33 #0.331 # CBO(2014) user_params['u_nc']
    u_array = np.array([u_c, u_nc])
    w = user_params['w']
    inv_credit = user_params['inv_credit']
    ace_c = user_params['ace_c']
    ace_nc = 0.
    ace_array = np.array([ace_c, ace_nc])
    r_ace = i
    int_haircut = user_params['int_haircut']
    bonus_deprec = user_params['bonus_deprec']
    deprec_system = user_params['deprec_system']
    # we don't have IP class in user params, so put here
    bonus_deprec['50'] = 0.
    deprec_system['50'] = 'ADS'
    # also for land and inventories which don't have tax deprec
    bonus_deprec['100'] = 0.
    deprec_system['100'] = 'ADS'

    # call tax calc to get individual rates
    if test_run==True:
        tau_nc = 0.33 # 0.331 # tax rate on non-corporate business income
        tau_div = 0.1757 #0.184 # tax rate on dividend income
        tau_int = 0.2379 # 0.274 # tax rate on interest income
        tau_scg = 0.3131 #0.323 # tax rate on short term capital gains
        tau_lcg = 0.222 #0.212 # tax rate on long term capital gains
        tau_xcg = 0.00 # tax rate on capital gains held to death
        tau_td = 0.215 # tax rate on return to equity held in tax deferred accounts
        tau_h = 0.181 # tax rate owner occupied housing deductions
        # test below is that calculator can be created
        CUR_PATH = os.path.abspath(os.path.dirname(__file__))
        TAXDATA_PATH = os.path.join(CUR_PATH,'test_data', 'puf91taxdata.csv.gz')
        TAXDATA = pd.read_csv(TAXDATA_PATH, compression='gzip')
        WEIGHTS_PATH = os.path.join(CUR_PATH,'test_data', 'puf91weights.csv.gz')
        WEIGHTS = pd.read_csv(WEIGHTS_PATH, compression='gzip')
        from btax.get_taxcalc_rates import get_calculator
        calc = get_calculator(baseline=False, calculator_start_year=start_year,
                              reform=iit_reform, data=TAXDATA,
                              weights=WEIGHTS, records_start_year=2009)
        assert calc.current_year == start_year
    else:
        from btax.get_taxcalc_rates import get_rates
        indiv_rates = get_rates(baseline,start_year,iit_reform)
        tau_nc = indiv_rates['tau_nc']
        tau_div = indiv_rates['tau_div']
        tau_int = indiv_rates['tau_int']
        tau_scg = indiv_rates['tau_scg']
        tau_lcg = indiv_rates['tau_lcg']
        tau_xcg = 0.00 # tax rate on capital gains held to death
        tau_td = indiv_rates['tau_td']
        tau_h = indiv_rates['tau_h']

    # Parameters for holding periods of assets, etc.
    Y_td = 8.
    Y_scg = 4/12.
    Y_lcg = 8.
    gamma = 0.3
    m = 0.4286

    #intermediate variables
    sprime_c_td = (1/Y_td)*np.log(((1-tau_td)*np.exp(i*Y_td))+tau_td)-pi
    s_c_d_td = gamma*(i-pi) + (1-gamma)*sprime_c_td
    s_c_d = alpha_c_d_ft*(((1-tau_int)*i)-pi) + alpha_c_d_td*s_c_d_td + alpha_c_d_nt*(i-pi)

    s_nc_d_td = s_c_d_td
    s_nc_d = alpha_nc_d_ft*(((1-tau_int)*i)-pi) + alpha_nc_d_td*s_nc_d_td + alpha_nc_d_nt*(i-pi)

    g_scg = (1/Y_scg)*np.log(((1-tau_scg)*np.exp((pi+m*E_c)*Y_scg))+tau_scg)-pi
    g_lcg = (1/Y_lcg)*np.log(((1-tau_lcg)*np.exp((pi+m*E_c)*Y_lcg))+tau_lcg)-pi
    g = omega_scg*g_scg + omega_lcg*g_lcg + omega_xcg*m*E_c
    s_c_e_ft = (1-m)*E_c*(1-tau_div)+g
    s_c_e_td = (1/Y_td)*np.log(((1-tau_td)*np.exp((pi+E_c)*Y_td))+tau_td)-pi
    s_c_e = alpha_c_e_ft*s_c_e_ft + alpha_c_e_td*s_c_e_td + alpha_c_e_nt*E_c

    s_c = f_c*s_c_d + (1-f_c)*s_c_e

    E_nc = s_c_e
    E_array = np.array([E_c, E_nc])
    s_nc_e = E_nc
    s_nc = f_nc*s_nc_d + (1-f_nc)*s_nc_e
    s_array = np.array([[s_c, s_nc], [s_c_d, s_nc_d], [s_c_e, s_nc_e]])

    r = f_array*(i*(1-(1-int_haircut)*u_array))+(1-f_array)*(E_array+pi - E_array*r_ace*ace_array)
    r_prime = f_array*i+(1-f_array)*(E_array+pi)
    delta = get_econ_depr()
    tax_methods = {'GDS 200%': 2.0, 'GDS 150%': 1.5, 'GDS SL': 1.0, 'ADS SL': 1.0}
    financing_list = ['', '_d', '_e']
    entity_list = ['_c', '_nc']
    z = calc_tax_depr_rates(r, delta, bonus_deprec, deprec_system, tax_methods, financing_list, entity_list)

    '''
    ------------------------------------------
    Define asset categories
    ------------------------------------------
    '''

    asset_categories = {'Computers and Software', 'Office and Residential Equipment',
        'Instruments and Communications Equipment', 'Transportation Equipment',
        'Industrial Machinery', 'Other Industrial Equipment', 'Other Equipment',
        'Residential Buildings', 'Nonresidential Buildings',
        'Mining and Drilling Structures', 'Other Structures'}


    asset_dict = dict.fromkeys(['Mainframes','PCs','DASDs','Printers',
          'Terminals','Tape drives','Storage devices','System integrators',
          'Prepackaged software','Custom software','Own account software'],'Computers and Software')
    asset_dict.update(dict.fromkeys(['Communications','Nonelectro medical instruments',
          'Electro medical instruments','Nonmedical instruments','Photocopy and related equipment',
          'Office and accounting equipment'],'Instruments and Communications Equipment'))
    asset_dict.update(dict.fromkeys(['Household furniture','Other furniture','Household appliances'],
          'Office and Residential Equipment'))
    asset_dict.update(dict.fromkeys(['Light trucks (including utility vehicles)',
          'Other trucks, buses and truck trailers','Autos','Aircraft',
          'Ships and boats','Railroad equipment','Steam engines','Internal combustion engines'],
          'Transportation Equipment'))
    asset_dict.update(dict.fromkeys(['Special industrial machinery','General industrial equipment'],
          'Industrial Machinery'))
    asset_dict.update(dict.fromkeys(['Nuclear fuel','Other fabricated metals',
          'Metalworking machinery','Electric transmission and distribution',
          'Other agricultural machinery','Farm tractors','Other construction machinery',
          'Construction tractors','Mining and oilfield machinery'],
          'Other Industrial Equipment'))
    asset_dict.update(dict.fromkeys(['Service industry machinery','Other electrical','Other'],
          'Other Equipment'))
    asset_dict.update(dict.fromkeys(['Residential'],
          'Residential Buildings'))
    asset_dict.update(dict.fromkeys(['Office','Hospitals','Special care','Medical buildings','Multimerchandise shopping',
          'Food and beverage establishments','Warehouses','Mobile structures','Other commercial',
          'Religious','Educational and vocational','Lodging'],
          'Nonresidential Buildings'))
    asset_dict.update(dict.fromkeys(['Gas','Petroleum pipelines','Communication',
          'Petroleum and natural gas','Mining'],'Mining and Drilling Structures'))
    asset_dict.update(dict.fromkeys(['Manufacturing','Electric','Wind and solar',
          'Amusement and recreation','Air transportation','Other transportation',
          'Other railroad','Track replacement','Local transit structures',
          'Other land transportation','Farm','Water supply','Sewage and waste disposal',
          'Public safety','Highway and conservation and development'],
          'Other Structures'))
    asset_dict.update(dict.fromkeys(['Pharmaceutical and medicine manufacturing',
          'Chemical manufacturing, ex. pharma and med','Semiconductor and other component manufacturing',
          'Computers and peripheral equipment manufacturing','Communications equipment manufacturing',
          'Navigational and other instruments manufacturing','Other computer and electronic manufacturing, n.e.c.',
          'Motor vehicles and parts manufacturing','Aerospace products and parts manufacturing',
          'Other manufacturing','Scientific research and development services','Software publishers',
          'Financial and real estate services','Computer systems design and related services','All other nonmanufacturing, n.e.c.',
          'Private universities and colleges','Other nonprofit institutions','Theatrical movies','Long-lived television programs',
          'Books','Music','Other entertainment originals'],'Intellectual Property'))

    # define major industry groupings
    major_industries = {'Agriculture, forestry, fishing, and hunting', 'Mining',
      'Utilities', 'Construction',
      'Manufacturing', 'Wholesale trade', 'Retail trade',
      'Transportation and warehousing', 'Information',
      'Finance and insurance', 'Real estate and rental and leasing',
      'Professional, scientific, and technical services',
      'Management of companies and enterprises', 'Administrative and waste management services',
      'Educational services', 'Health care and social assistance',
      'Arts, entertainment, and recreation', 'Accommodation and food services',
      'Other services, except government'}
    ind_dict = dict.fromkeys(['Farms','Forestry, fishing, and related activities'],
                              'Agriculture, forestry, fishing, and hunting')
    ind_dict.update(dict.fromkeys(['Oil and gas extraction',
        'Mining, except oil and gas','Support activities for mining'],'Mining'))
    ind_dict.update(dict.fromkeys(['Utilities'],'Utilities'))
    ind_dict.update(dict.fromkeys(['Construction'],'Construction'))
    ind_dict.update(dict.fromkeys(['Wood products', 'Nonmetallic mineral products',
                                  'Primary metals', 'Fabricated metal products',
                                  'Machinery','Computer and electronic products',
                                  'Electrical equipment, appliances, and components',
                                  'Motor vehicles, bodies and trailers, and parts',
                                  'Other transportation equipment',
                                  'Furniture and related products',
                                  'Miscellaneous manufacturing',
                                  'Food, beverage, and tobacco products',
                                  'Textile mills and textile products',
                                  'Apparel and leather and allied products',
                                  'Paper products', 'Printing and related support activities',
                                  'Petroleum and coal products', 'Chemical products',
                                  'Plastics and rubber products'],'Manufacturing'))
    ind_dict.update(dict.fromkeys(['Wholesale trade'],'Wholesale trade'))
    ind_dict.update(dict.fromkeys(['Retail trade'],'Retail trade'))
    ind_dict.update(dict.fromkeys(['Air transportation', 'Railroad transportation',
                                  'Water transportation', 'Truck transportation',
                                  'Transit and ground passenger transportation',
                                  'Pipeline transportation',
                                  'Other transportation and support activitis',
                                  'Warehousing and storage'],'Transportation and warehousing'))
    ind_dict.update(dict.fromkeys(['Publishing industries (including software)',
                                  'Motion picture and sound recording industries',
                                  'Broadcasting and telecommunications',
                                  'Information and telecommunications'],
                                  'Information'))
    ind_dict.update(dict.fromkeys(['Federal Reserve banks',
                              'Credit intermediation and related activities',
                              'Securities, commodity contracts, and investments',
                              'Insurance carriers and related activities',
                              'Funds, trusts, and other financial vehicles'],
                          'Finance and insurance'))
    ind_dict.update(dict.fromkeys(['Real estate',
                          'Rental and leasing services and lessors of intangible assets'],
                          'Real estate and rental and leasing'))
    ind_dict.update(dict.fromkeys(['Legal services',
                          'Computer systems design and related services',
                          'Miscellaneous professional, scientific, and technical services'],
                          'Professional, scientific, and technical services'))
    ind_dict.update(dict.fromkeys(['Management of companies and enterprises'],
                          'Management of companies and enterprises'))
    ind_dict.update(dict.fromkeys(['Administrative and support services',
                          'Waster management and remediation services'],
                          'Administrative and waste management services'))
    ind_dict.update(dict.fromkeys(['Educational services'],
                          'Educational services'))
    ind_dict.update(dict.fromkeys(['Ambulatory health care services',
                          'Hospitals', 'Nursing and residential care facilities',
                          'Social assistance'],
                          'Health care and social assistance'))
    ind_dict.update(dict.fromkeys(['Performing arts, spectator sports, museums, and related activities',
                          'Amusements, gambling, and recreation industries'],
                          'Arts, entertainment, and recreation'))
    ind_dict.update(dict.fromkeys(['Accomodation',
                          'Food services and drinking places'],
                          'Accommodation and food services'))
    ind_dict.update(dict.fromkeys(['Other services, except government'],
                          'Other services, except government'))



    parameters = {'inflation rate': pi,
        'econ depreciation': delta,
        'depr allow': z,
        'tax rate': u_array,
        'discount rate': r,
        'after-tax rate': r_prime,
        'return to savers': s_array,
        'prop tax': w,
        'inv_credit': inv_credit,
        'ace':ace_array,
        'int_haircut':int_haircut,
        'financing_list':financing_list,
        'entity_list':entity_list,
        'delta': delta,
        'asset_dict': asset_dict,
        'ind_dict': ind_dict
    }
    return parameters
