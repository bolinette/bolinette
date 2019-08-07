from bolinette import Namespace, transactional, response
from bolinette.marshalling import returns, expects
from example.services import book_service

ns = Namespace('book', '/book')


@ns.route('')
@returns('book', as_list=True)
def get_books():
    return response.ok('OK', book_service.get_all())


@ns.route('/<book_id>', methods=['GET'])
@returns('book', 'complete')
@transactional
def get_book(book_id):
    return response.ok('OK', book_service.get(book_id))


ns.register()
