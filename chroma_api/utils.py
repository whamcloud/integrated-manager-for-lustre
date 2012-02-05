
from hydraapi.requesthandler import APIResponse


def paginate_result(page_id, page_size, result, format_fn, sEcho = None):
    """Paginate a django QuerySet into the form expected by jquery.datatables"""
    if page_id:
        offset = int(page_id)
    else:
        offset = 0
    # iTotalRecords is the number of records before filtering (where here filtering
    # means datatables filtering, not the filtering we're doing from our other args)
    iTotalRecords = result.count()
    # This is equal because we are not doing any datatables filtering here yet.
    iTotalDisplayRecords = iTotalRecords

    if page_size:
        result = result[offset:offset + page_size]

    # iTotalDisplayRecords is simply the number of records we will return
    # in this call (i.e. after all filtering and pagination)
    paginated_result = {}
    paginated_result['iTotalRecords'] = iTotalRecords
    paginated_result['iTotalDisplayRecords'] = iTotalDisplayRecords
    paginated_result['aaData'] = [format_fn(r) for r in result]
    if sEcho:
        paginated_result['sEcho'] = int(sEcho)

    # Use cache=False to get some anti-caching headers set on the
    # HTTP response: necessary because /event/?iDisplayStart=0 is
    # actually something that changes due to backwards-time-sorting.
    return APIResponse(paginated_result, 200, cache = False)
