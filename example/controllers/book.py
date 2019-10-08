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


@ns.route('', methods=['POST'])
@returns('book', 'complete')
@transactional
@expects('book')
def create_book(payload):
    return response.created('book.created', book_service.create(payload))


@ns.route('/<book_id>', methods=['PUT'])
@returns('book', 'complete')
@transactional
@expects('book', update=True)
def update_book(book_id, payload):
    book = book_service.get(book_id)
    return response.ok('book.updated', book_service.update(book, payload))


@ns.route('/<book_id>', methods=['DELETE'])
@returns('book', 'complete')
@transactional
def delete_book(book_id):
    book = book_service.get(book_id)
    return response.ok('book.deleted', book_service.delete(book))


ns.register()
