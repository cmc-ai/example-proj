# docker image build -t katabat/example_lambda:TAG .
# docker run --rm -it katabat/example_lambda:TAG

FROM public.ecr.aws/lambda/python:3.8

WORKDIR /app

# Python dependencies
ADD requirements.txt /app
RUN pip3 install -r requirements.txt

COPY lambda_function.py  .

CMD [ "/app/lambda_function.lambda_handler" ]