import logging
import random
import string

from scrapy.http import FormRequest
from scrapy.http.request.form import _get_inputs as get_form_data


logger = logging.getLogger(__name__)

SEARCH_TERMS = list(string.ascii_lowercase) + list('123456789 *%.?')


def _fill_form(search_term, form, meta, do_random_refinement=False):
    additional_formdata = {}
    search_fields = []
    for input_name, input_type in meta['fields'].items():
        input_el = form.inputs[input_name]
        if input_type == 'search query':
            search_fields.append(input_name)
        elif do_random_refinement and refinement_input(input_type, input_el):
            if input_el.type == 'checkbox' and random.random() > 0.5:
                additional_formdata[input_name] = 'on'
    additional_formdata[random.choice(search_fields)] = search_term
    return get_form_data(form, additional_formdata, None, None, None)


def refinement_input(input_type, input_el):
    return (input_type == 'search category / refinement' and
            getattr(input_el, 'type', None) in ['checkbox'])


def search_form_requests(url, form, meta, extra_search_terms=None, **kwargs):
    refinement_options = [False]
    if not any(input_type == 'search query'
               for input_type in meta['fields'].values()):
        return
    n_target_inputs = sum(
        input_type == 'search query' or
        refinement_input(input_type, form.inputs[input_name])
        for input_name, input_type in meta['fields'].items())
    assert n_target_inputs >= 0
    # 2 and 4 here are just some values that feel right, need tuning
    refinement_options.append([True] * 2 * min(4, n_target_inputs))

    search_terms = sorted(set(list(extra_search_terms or []) + SEARCH_TERMS))
    for search_term in search_terms:
        for do_random_refinement in refinement_options:
            formdata = _fill_form(
                search_term, form, meta, do_random_refinement)
            if formdata is not None:
                yield FormRequest(
                    url=url,
                    formdata=formdata,
                    method=form.method,
                    priority=-15,
                    **kwargs)
