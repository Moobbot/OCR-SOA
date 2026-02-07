from .positions import PositionsPlugin
from .trade_information import TradeInformationPlugin
from .fx_tf import FXTFPlugin
from .others import OthersPlugin


def get_all_plugins(rules):
    return [
        PositionsPlugin(rules),
        TradeInformationPlugin(rules),
        FXTFPlugin(rules),
        OthersPlugin(rules),
    ]
