import string

from scrapy.http import FormRequest
from scrapy.http.request.form import _get_inputs as get_form_data


SEARCH_TERMS = list(string.ascii_lowercase) + [' ', '*' , '%', '.', '?']


def _fill_form(search_term, form, meta):
    additional_formdata = {}
    for input_, input_type in meta['fields'].items():
        if input_type == 'search query':
            additional_formdata[input_] = search_term
    if additional_formdata:
        return get_form_data(form, additional_formdata, None, None, None)


def search_form_requests(url, form, meta, **kwargs):
    for search_term in SEARCH_TERMS:
        formdata = _fill_form(search_term, form, meta)
        if formdata is not None:
            yield FormRequest(
                url=url, formdata=formdata, method=form.method, **kwargs)
