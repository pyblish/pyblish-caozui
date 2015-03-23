import pyblish.plugin
import pyblish.api

@pyblish.api.log
class Selector(pyblish.plugin.Selector):
    status = 0
    fixable = 0
    override = False

@pyblish.api.log
class Validator(pyblish.plugin.Validator):
    status = 0
    fixable = 0
    override = False

@pyblish.api.log
class Extractor(pyblish.plugin.Extractor):
    status = 0
    fixable = 0
    override = False

@pyblish.api.log
class Conformer(pyblish.plugin.Conformer):
    status = 0
    fixable = 0
    override = False

    def add_snapshot(self, snapshot_code, context):
        element_snapshot_codes = context.data('element_snapshot_codes', [])
        element_snapshot_codes.append(snapshot_code)
        context.set_data('element_snapshot_codes', element_snapshot_codes)

    def snapshots(self, context):
        return context.data('element_snapshot_codes', [])
