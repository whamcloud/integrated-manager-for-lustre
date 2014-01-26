jasmine-n-matchers
==================

A set of matchers to assert a spy was called n times


## Usage

Make sure the jasmine-n-matchers.js file is executed early in your tests, it uses `beforeEach` to register the matchers.

## Example

```javascript
var spy = jasmine.createSpy('spy');

expect(spy).toHaveBeenCalledNTimes(0);

spy('foo', 'bar');

expect(spy).toHaveBeenCalledNTimes(1);
expect(spy).toHaveBeenCalledOnce();
expect(spy).toHaveBeenCalledOnceWith('foo', 'bar');

spy('foo', 'bar');

expect(spy).toHaveBeenCalledNTimes(2);
expect(spy).toHaveBeenCalledTwice();
expect(spy).toHaveBeenCalledTwiceWith('foo', 'bar');

spy('bar', 'baz');

expect(spy).toHaveBeenCalledNTimes(3);
expect(spy).toHaveBeenCalledThrice();
expect(spy).toHaveBeenCalledTwiceWith('foo', 'bar');
expect(spy).toHaveBeenCalledOnceWith('bar', 'baz');

spy('foo', 'bar');
spy('foo', 'bar');

expect(spy).toHaveBeenCalledNTimes(5);
expect(spy).toHaveBeenCalledNTimesWith(4, 'foo', 'bar');
