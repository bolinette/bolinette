from bolinette.core import Bolinette, Environment, Logger


if __name__ == '__main__':
    blnt = Bolinette()
    logger = blnt.injection.require(Logger)
    logger.info('Test info')
    logger.debug('Test debug')
    logger.warning('Test warning')
    logger.error('Test error')
