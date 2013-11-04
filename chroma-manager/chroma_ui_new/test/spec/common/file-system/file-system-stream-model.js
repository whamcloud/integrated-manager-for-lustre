describe('file system stream model', function () {
  'use strict';

  var FileSystemStreamModel, value;

  beforeEach(module('fileSystem'));

  beforeEach(inject(function (_FileSystemStreamModel_) {
    FileSystemStreamModel = _FileSystemStreamModel_;

    value = {
      a: 'b',
      bytes_free: 10000,
      bytes_total: 100000,
      files_free: 50000,
      files_total: 500000,
      immutable_state: true
    };
  }));

  describe('instantiating', function () {
    var fileSystemStreamModel;

    beforeEach(function () {
      fileSystemStreamModel = new FileSystemStreamModel(value);
    });

    it('should add the value passed into the constructor to the instance', function () {
      expect(fileSystemStreamModel.a).toBe('b');
    });

    it('should calculate space graph data', function () {
      expect(fileSystemStreamModel.spaceGraphData).toEqual([
        { key : 'Free', y : 10000 },
        { key : 'Used', y : 90000 }
      ]);
    });

    it('should calculate usage graph data', function () {
      expect(fileSystemStreamModel.usageGraphData).toEqual([
        { key : 'Free', y : 50000 },
        { key : 'Used', y : 450000 }
      ]);
    });

    it('should return the current state', function () {
      expect(fileSystemStreamModel.getState()).toBe('monitored');
    });

    it('should return the used space', function () {
      expect(fileSystemStreamModel.getUsedSpace()).toBe('87.89 KB');
    });

    it('should return the total space', function () {
      expect(fileSystemStreamModel.getTotalSpace()).toBe('97.66 KB');
    });

    it('should return the used files', function () {
      expect(fileSystemStreamModel.getUsedFiles()).toBe('450k');
    });

    it('should return the total files', function () {
      expect(fileSystemStreamModel.getTotalFiles()).toBe('500k');
    });
  });
});